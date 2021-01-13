from os import path, environ, mkdir, listdir, remove
from os.path import isdir
from subprocess import run, CalledProcessError
from shutil import rmtree
from threading import Thread
from marshmallow import ValidationError
from models.magic_castle.magic_castle_configuration import MagicCastleConfiguration
from models.magic_castle.cluster_status_code import ClusterStatusCode
from models.magic_castle.plan_type import PlanType
from models.terraform.terraform_state_parser import TerraformStateParser
from models.terraform.terraform_plan_parser import TerraformPlanParser
from models.cloud.cloud_manager import CloudManager
from models.cloud.dns_manager import DnsManager
from models.puppet.provisioning_manager import ProvisioningManager
from exceptions.invalid_usage_exception import *
from exceptions.server_exception import *
from models.constants import TERRAFORM_STATE_FILENAME, CLUSTERS_PATH
from database.database_manager import DatabaseManager
import sqlite3
import logging
import re
import json


DEFAULT_CLOUD = "openstack"

TERRAFORM_PLAN_BINARY_FILENAME = "terraform_plan"
TERRAFORM_PLAN_JSON_FILENAME = "terraform_plan.json"

TERRAFORM_APPLY_LOG_FILENAME = "terraform_apply.log"
TERRAFORM_PLAN_LOG_FILENAME = "terraform_plan.log"


class MagicCastle:
    """
    Magic Castle is the class that manages the state of Magic Castle clusters.
    It is responsible for building, modifying and destroying clusters using Terraform.
    It is also used to parse the state of existing clusters and return it in
    a simple dictionary format.
    """

    def __init__(
        self, database_connection: sqlite3.Connection, hostname=None, owner=None
    ):
        self.__database_connection = database_connection
        self.__hostname = hostname
        self.__owner = owner
        self.__configuration = None
        self.__status = None
        self.__plan_type = None

    def get_hostname(self):
        return self.__hostname

    def get_cluster_name(self):
        return self.__hostname.split(".", 1)[0]

    def get_domain(self):
        return self.__hostname.split(".", 1)[1]

    def get_owner(self):
        if self.__owner is None:
            result = self.__database_connection.execute(
                "SELECT owner FROM magic_castles WHERE hostname = ?",
                (self.get_hostname(),),
            ).fetchone()
            if result:
                self.__owner = result[0]
            else:
                self.__owner = None
        return self.__owner

    def get_owner_username(self):
        """
        MC Hub stores username in the form of eduPersonPrincipalName.
        """
        owner = self.get_owner()
        if owner:
            return owner.split("@")[0]
        return None

    def load_configuration(self, configuration: dict):
        try:
            self.__configuration = MagicCastleConfiguration.get_from_dict(configuration)
            self.__hostname = self.__configuration.get_hostname()
        except ValidationError:
            raise InvalidUsageException(
                "The magic castle configuration could not be parsed"
            )

    def get_status(self) -> ClusterStatusCode:
        if self.__status is None:
            result = self.__database_connection.execute(
                "SELECT status FROM magic_castles WHERE hostname = ?",
                (self.get_hostname(),),
            ).fetchone()
            if result:
                self.__status = ClusterStatusCode(result[0])
            else:
                self.__status = ClusterStatusCode.NOT_FOUND
        return self.__status

    def __update_status(self, status: ClusterStatusCode):
        self.__status = status
        self.__database_connection.execute(
            "UPDATE magic_castles SET status = ? WHERE hostname = ?",
            (self.__status.value, self.__hostname),
        )
        self.__database_connection.commit()

        # Log cluster status updates for log analytics
        print(
            json.dumps(
                {
                    "hostname": self.get_hostname(),
                    "status": self.__status.value,
                    "owner": self.get_owner(),
                }
            ),
            flush=True,
        )

    def get_plan_type(self) -> PlanType:
        if self.__plan_type is None:
            result = self.__database_connection.execute(
                "SELECT plan_type FROM magic_castles WHERE hostname = ?",
                (self.get_hostname(),),
            ).fetchone()
            if result:
                self.__plan_type = PlanType(result[0])
            else:
                self.__plan_type = PlanType.NONE
        return self.__plan_type

    def __update_plan_type(self, plan_type: PlanType):
        self.__plan_type = plan_type
        self.__database_connection.execute(
            "UPDATE magic_castles SET plan_type = ? WHERE hostname = ?",
            (self.__plan_type.value, self.__hostname),
        )
        self.__database_connection.commit()

    def get_progress(self):
        if self.__not_found():
            raise ClusterNotFoundException

        initial_plan = self.__get_plan()
        if initial_plan is None:
            return None
        try:
            with open(
                self.__get_cluster_path(TERRAFORM_APPLY_LOG_FILENAME), "r"
            ) as file:
                terraform_output = file.read()
        except FileNotFoundError:
            # terraform apply was not launched yet, therefore the log file does not exist
            terraform_output = ""
        return TerraformPlanParser.get_done_changes(initial_plan, terraform_output)

    def dump_configuration(self):
        """
        Returns the Magic Castle configuration dictionary of the current cluster.
        To do so, it first attempts to read the terraform.tfstate file to parse the configuration.
        If the file does not exist (for a cluster that isn't built yet), it parses the configuration
        from the main.tf.json file (which contains less information).
        """
        if self.__not_found():
            raise ClusterNotFoundException

        try:
            self.__configuration = MagicCastleConfiguration.get(self.get_hostname())
            return self.__configuration.dump()
        except FileNotFoundError:
            return dict()

    def get_freeipa_passwd(self):
        if self.__is_busy():
            return None

        try:
            with open(
                self.__get_cluster_path(TERRAFORM_STATE_FILENAME), "r"
            ) as terraform_state_file:
                state = json.load(terraform_state_file)
                return TerraformStateParser(state).get_freeipa_passwd()
        except FileNotFoundError:
            return None

    def get_available_resources(self):
        if self.__is_busy():
            raise BusyClusterException

        try:
            with open(
                self.__get_cluster_path(TERRAFORM_STATE_FILENAME), "r"
            ) as terraform_state_file:
                state = json.load(terraform_state_file)
            parser = TerraformStateParser(state)

            cloud_manager = CloudManager(
                pre_allocated_instance_count=parser.get_instance_count(),
                pre_allocated_ram=parser.get_ram(),
                pre_allocated_cores=parser.get_cores(),
                pre_allocated_volume_count=parser.get_volume_count(),
                pre_allocated_volume_size=parser.get_volume_size(),
                pre_allocated_floating_ips=parser.get_os_floating_ips(),
            )
        except FileNotFoundError:
            cloud_manager = CloudManager()

        return cloud_manager.get_available_resources()

    def __is_busy(self):
        return self.get_status() in [
            ClusterStatusCode.PLAN_RUNNING,
            ClusterStatusCode.BUILD_RUNNING,
            ClusterStatusCode.DESTROY_RUNNING,
        ]

    def __not_found(self):
        return self.get_status() == ClusterStatusCode.NOT_FOUND

    def __plan_created(self):
        return self.get_status() != ClusterStatusCode.PLAN_RUNNING and path.exists(
            self.__get_cluster_path(TERRAFORM_PLAN_BINARY_FILENAME)
        )

    def __found(self):
        return self.get_status() != ClusterStatusCode.NOT_FOUND

    def __get_cluster_path(self, sub_path=""):
        """
        Returns the absolute path of the current cluster folder.
        If sub_path is specified, it is appended to the cluster path.
        """
        if self.get_hostname():
            return path.join(CLUSTERS_PATH, self.get_hostname(), sub_path)
        else:
            raise FileNotFoundError

    def plan_creation(self):
        if self.__found():
            raise ClusterExistsException

        return self.__plan(destroy=False, existing_cluster=False)

    def plan_modification(self):
        if self.__not_found():
            raise ClusterNotFoundException
        if self.__is_busy():
            raise BusyClusterException

        return self.__plan(destroy=False, existing_cluster=True)

    def plan_destruction(self):
        if self.__not_found():
            raise ClusterNotFoundException
        if self.__is_busy():
            raise BusyClusterException

        self.__plan(destroy=True, existing_cluster=True)

    def __plan(self, *, destroy, existing_cluster):
        plan_type = PlanType.DESTROY if destroy else PlanType.BUILD
        if existing_cluster:
            self.__remove_existing_plan()
            previous_status = self.get_status()
        else:
            self.__database_connection.execute(
                "INSERT INTO magic_castles (hostname, cluster_name, domain, status, plan_type, owner) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    self.get_hostname(),
                    self.get_cluster_name(),
                    self.get_domain(),
                    ClusterStatusCode.CREATED.value,
                    plan_type.value,
                    self.get_owner(),
                ),
            )
            mkdir(self.__get_cluster_path())
            previous_status = ClusterStatusCode.CREATED

        self.__update_status(ClusterStatusCode.PLAN_RUNNING)
        self.__update_plan_type(plan_type)

        if not destroy:
            self.__configuration.update_main_tf_json_file()

        try:
            run(
                ["terraform", "init", "-no-color", "-input=false"],
                cwd=self.__get_cluster_path(),
                capture_output=True,
                check=True,
            )
        except CalledProcessError:
            self.__update_status(previous_status)
            logging.error("An error occurred while initializing Terraform")
            return

        with open(
            self.__get_cluster_path(TERRAFORM_PLAN_LOG_FILENAME), "w"
        ) as output_file:
            environment_variables = environ.copy()
            dns_manager = DnsManager(self.get_domain())
            environment_variables.update(dns_manager.get_environment_variables())
            environment_variables["OS_CLOUD"] = DEFAULT_CLOUD
            try:
                run(
                    [
                        "terraform",
                        "plan",
                        "-input=false",
                        "-no-color",
                        "-destroy=" + ("true" if destroy else "false"),
                        "-out="
                        + self.__get_cluster_path(TERRAFORM_PLAN_BINARY_FILENAME),
                    ],
                    cwd=self.__get_cluster_path(),
                    env=environment_variables,
                    stdout=output_file,
                    stderr=output_file,
                    check=True,
                )
            except CalledProcessError:
                if destroy:
                    # Terraform returns an error if we try to destroy a cluster when the image
                    # it was created with does not exist anymore (e.g. CentOS-7-x64-2019-07). In these cases,
                    # not refreshing the terraform state (refresh=false) solves the issue.
                    try:
                        run(
                            [
                                "terraform",
                                "plan",
                                "-refresh=false",
                                "-input=false",
                                "-no-color",
                                "-destroy=" + ("true" if destroy else "false"),
                                "-out="
                                + self.__get_cluster_path(
                                    TERRAFORM_PLAN_BINARY_FILENAME
                                ),
                            ],
                            cwd=self.__get_cluster_path(),
                            env=environment_variables,
                            stdout=output_file,
                            stderr=output_file,
                            check=True,
                        )
                    except CalledProcessError:
                        # terraform plan fails even without refreshing the state
                        self.__update_status(previous_status)
                        logging.error(
                            "An error occurred while creating the Terraform plan"
                        )
                        return
                else:
                    self.__update_status(previous_status)
                    logging.error("An error occurred while creating the Terraform plan")
                    return

            with open(
                self.__get_cluster_path(TERRAFORM_PLAN_JSON_FILENAME), "w"
            ) as output_file:
                try:
                    run(
                        ["terraform", "show", "-json", TERRAFORM_PLAN_BINARY_FILENAME],
                        cwd=self.__get_cluster_path(),
                        stdout=output_file,
                        check=True,
                    )
                except CalledProcessError:
                    self.__update_status(previous_status)
                    logging.error(
                        "An error occurred while exporting the json Terraform plan"
                    )
                    return

        self.__update_status(previous_status)

    def apply(self):
        if self.__not_found():
            raise ClusterNotFoundException
        if self.__is_busy():
            raise BusyClusterException
        if not self.__plan_created():
            raise PlanNotCreatedException

        self.__update_status(
            ClusterStatusCode.BUILD_RUNNING
            if self.get_plan_type() == PlanType.BUILD
            else ClusterStatusCode.DESTROY_RUNNING
        )

        def terraform_apply(destroy: bool):
            try:
                with open(
                    self.__get_cluster_path(TERRAFORM_APPLY_LOG_FILENAME), "w"
                ) as output_file:
                    environment_variables = environ.copy()
                    dns_manager = DnsManager(self.get_domain())
                    environment_variables.update(
                        dns_manager.get_environment_variables()
                    )
                    environment_variables["OS_CLOUD"] = DEFAULT_CLOUD
                    if destroy:
                        environment_variables["TF_WARN_OUTPUT_ERRORS"] = "1"
                    run(
                        [
                            "terraform",
                            "apply",
                            "-input=false",
                            "-no-color",
                            "-auto-approve",
                            self.__get_cluster_path(TERRAFORM_PLAN_BINARY_FILENAME),
                        ],
                        cwd=self.__get_cluster_path(),
                        stdout=output_file,
                        stderr=output_file,
                        check=True,
                        env=environment_variables,
                    )
                with DatabaseManager.connect() as database_connection:
                    self.__database_connection = database_connection
                    if destroy:
                        # Removes the content of the cluster's folder, even if not empty
                        rmtree(self.__get_cluster_path(), ignore_errors=True)
                        self.__database_connection.execute(
                            "DELETE FROM magic_castles WHERE hostname = ?",
                            (self.get_hostname(),),
                        )
                        self.__database_connection.commit()
                    else:
                        self.__update_status(ClusterStatusCode.PROVISIONING_RUNNING)

                if not destroy:
                    provisioning_manager = ProvisioningManager(self.get_hostname())

                    # Avoid multiple threads polling the same cluster
                    if not provisioning_manager.is_busy():
                        try:
                            provisioning_manager.poll_until_success()
                            status_code = ClusterStatusCode.PROVISIONING_SUCCESS
                        except PuppetTimeoutException:
                            status_code = ClusterStatusCode.PROVISIONING_ERROR

                        with DatabaseManager.connect() as database_connection:
                            self.__database_connection = database_connection
                            self.__update_status(status_code)

            except CalledProcessError:
                logging.info("An error occurred while running terraform apply")
                with DatabaseManager.connect() as database_connection:
                    self.__database_connection = database_connection
                    self.__update_status(
                        ClusterStatusCode.DESTROY_ERROR
                        if destroy
                        else ClusterStatusCode.BUILD_ERROR
                    )
            finally:
                with DatabaseManager.connect() as database_connection:
                    self.__database_connection = database_connection
                    self.__remove_existing_plan()

        destroy = self.get_plan_type() == PlanType.DESTROY
        terraform_apply_thread = Thread(target=terraform_apply, args=(destroy,))
        terraform_apply_thread.start()

    def __remove_existing_plan(self):
        try:
            self.__update_plan_type(PlanType.NONE)
            # Remove existing plan, if it exists
            remove(self.__get_cluster_path(TERRAFORM_PLAN_BINARY_FILENAME))
            remove(self.__get_cluster_path(TERRAFORM_PLAN_JSON_FILENAME))
        except FileNotFoundError:
            # Must be a new cluster, without existing plans
            pass

    def __get_plan(self):
        try:
            with open(
                self.__get_cluster_path(TERRAFORM_PLAN_JSON_FILENAME), "r"
            ) as plan_file:
                plan_object = json.load(plan_file)
            return plan_object
        except (FileNotFoundError, json.decoder.JSONDecodeError):
            return None
