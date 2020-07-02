from os import path, environ, mkdir, listdir, remove
from os.path import isdir
from flask import render_template
from subprocess import run, CalledProcessError
from shutil import rmtree
from threading import Thread
from marshmallow import ValidationError
from models.cluster_status_code import ClusterStatusCode
from models.plan_type import PlanType
from models.magic_castle_schema import MagicCastleSchema
from models.terraform_state_parser import TerraformStateParser
from models.terraform_plan_parser import TerraformPlanParser
from models.openstack_manager import OpenStackManager
from exceptions.invalid_usage_exception import InvalidUsageException
from exceptions.busy_cluster_exception import BusyClusterException
from exceptions.cluster_not_found_exception import ClusterNotFoundException
from exceptions.cluster_exists_exception import ClusterExistsException
from exceptions.plan_not_created_exception import PlanNotCreatedException
from exceptions.state_not_found_exception import StateNotFoundException
import logging
import re
import json

MAGIC_CASTLE_RELEASE_PATH = path.join(
    environ["HOME"], "magic_castle-openstack-" + environ["MAGIC_CASTLE_VERSION"]
)
CLUSTERS_PATH = path.join(environ["HOME"], "clusters")

STATUS_FILENAME = "status.txt"
PLAN_TYPE_FILENAME = "plan_type.txt"
TERRAFORM_STATE_FILENAME = "terraform.tfstate"
TERRAFORM_PLAN_BINARY_FILENAME = "terraform_plan"
TERRAFORM_PLAN_JSON_FILENAME = "terraform_plan.json"

TERRAFORM_APPLY_LOG_FILENAME = "terraform_apply.log"
TERRAFORM_PLAN_LOG_FILENAME = "terraform_plan.log"


class MagicCastle:
    """
    Magic Castle is the class that manages the state of Magic Castle clusters.
    It is responsible for building, modifying and destroying clusters.
    It is also used to parse the state of existing clusters and return it in
    a simple dictionary format.
    """

    def __init__(self, hostname=None):
        self.__configuration = {}
        self.__status = None
        self.__plan_type = None
        if self.validate_hostname(hostname):
            [cluster_name, domain] = hostname.split(".", 1)
            self.__configuration["cluster_name"] = cluster_name
            self.__configuration["domain"] = domain

    @classmethod
    def all(cls):
        """
        Retrieve all the Magic Castles in the clusters folder.
        :return: A list of MagicCastle objects
        """
        return [
            cls(hostname)
            for hostname in sorted(listdir(CLUSTERS_PATH))
            if isdir(path.join(CLUSTERS_PATH, hostname))
        ]

    def validate_hostname(self, hostname):
        return (
            hostname
            and re.search(r"^[a-z][a-z0-9]*(\.[a-z0-9]+)+$", hostname) is not None
        )

    def get_hostname(self):
        cluster_name = self.__configuration.get("cluster_name")
        domain = self.__configuration.get("domain")
        if cluster_name and domain:
            return f"{cluster_name}.{domain}"
        else:
            return None

    def get_cluster_name(self):
        return self.__configuration.get("cluster_name")

    def get_domain(self):
        return self.__configuration.get("domain")

    def load_configuration(self, configuration: dict):
        try:
            self.__configuration = MagicCastleSchema().load(configuration)
        except ValidationError:
            raise InvalidUsageException(
                "The magic castle configuration could not be parsed"
            )

        # When modifying a cluster, the existing floating ip must be excluded
        # from the configuration, as it does not look available to Open Stack.
        available_floating_ips = set(OpenStackManager().get_available_floating_ips())
        if not set(self.__configuration["os_floating_ips"]).issubset(
            available_floating_ips
        ):
            self.__configuration["os_floating_ips"] = []

    def get_status(self) -> ClusterStatusCode:
        if self.__status is None:
            status_file_path = self.__get_cluster_path(STATUS_FILENAME)
            if not status_file_path or not path.exists(status_file_path):
                self.__status = ClusterStatusCode.NOT_FOUND
                return self.__status
            with open(status_file_path, "r") as status_file:
                self.__status = ClusterStatusCode(status_file.read())
        return self.__status

    def __update_status(self, status: ClusterStatusCode):
        logging.debug(
            f"Updating status for {self.get_cluster_name()} with {status.value}"
        )
        self.__status = status
        with open(self.__get_cluster_path(STATUS_FILENAME), "w") as status_file:
            status_file.write(status.value)

    def get_plan_type(self) -> PlanType:
        if self.__plan_type is None:
            with open(
                self.__get_cluster_path(PLAN_TYPE_FILENAME), "r"
            ) as plan_type_file:
                self.__plan_type = PlanType(plan_type_file.read())
        return self.__plan_type

    def __update_plan_type(self, plan_type: PlanType):
        self.__plan_type = plan_type
        with open(self.__get_cluster_path(PLAN_TYPE_FILENAME), "w") as plan_type_file:
            plan_type_file.write(plan_type.value)

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

    def get_state(self):
        if self.__is_busy():
            raise BusyClusterException
        if self.__not_found():
            raise ClusterNotFoundException

        try:
            with open(
                self.__get_cluster_path(TERRAFORM_STATE_FILENAME), "r"
            ) as terraform_state_file:
                state = json.load(terraform_state_file)
            parser = TerraformStateParser(state)
            return MagicCastleSchema().dump(parser.get_state_summary())
        except FileNotFoundError:
            raise StateNotFoundException

    def get_available_resources(self):
        if self.__is_busy():
            raise BusyClusterException

        try:
            if self.__found():
                with open(
                    self.__get_cluster_path(TERRAFORM_STATE_FILENAME), "r"
                ) as terraform_state_file:
                    state = json.load(terraform_state_file)
                parser = TerraformStateParser(state)

                openstack_manager = OpenStackManager(
                    pre_allocated_instance_count=parser.get_instance_count(),
                    pre_allocated_ram=parser.get_ram(),
                    pre_allocated_cores=parser.get_cores(),
                    pre_allocated_volume_count=parser.get_volume_count(),
                    pre_allocated_volume_size=parser.get_volume_size(),
                    pre_allocated_floating_ips=parser.get_os_floating_ips(),
                )
            else:
                openstack_manager = OpenStackManager()

            return openstack_manager.get_available_resources()
        except FileNotFoundError:
            raise StateNotFoundException

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
        if self.get_hostname():
            return path.join(CLUSTERS_PATH, self.get_hostname(), sub_path)
        else:
            return None

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
        if existing_cluster:
            self.__remove_existing_plan()
            previous_status = self.get_status()
        else:
            mkdir(self.__get_cluster_path())
            previous_status = ClusterStatusCode.CREATED

        self.__update_status(ClusterStatusCode.PLAN_RUNNING)
        self.__update_plan_type(PlanType.DESTROY if destroy else PlanType.BUILD)

        if not destroy:
            with open(self.__get_cluster_path("main.tf"), "w") as cluster_config_file:
                cluster_config_file.write(
                    render_template(
                        "main.tf",
                        **self.__configuration,
                        magic_castle_release_path=MAGIC_CASTLE_RELEASE_PATH,
                    )
                )

        try:
            run(
                [
                    "terraform",
                    "init",
                    "-no-color",
                    "-plugin-dir",
                    environ["HOME"] + "/.terraform.d/plugin-cache/linux_amd64",
                ],
                cwd=self.__get_cluster_path(),
                capture_output=True,
                check=True,
            )
            with open(
                self.__get_cluster_path(TERRAFORM_PLAN_LOG_FILENAME), "w"
            ) as output_file:
                run(
                    [
                        "terraform",
                        "plan",
                        "-no-color",
                        "-destroy=" + ("true" if destroy else "false"),
                        "-out="
                        + self.__get_cluster_path(TERRAFORM_PLAN_BINARY_FILENAME),
                    ],
                    cwd=self.__get_cluster_path(),
                    stdout=output_file,
                    stderr=output_file,
                    check=True,
                )
            with open(
                self.__get_cluster_path(TERRAFORM_PLAN_JSON_FILENAME), "w"
            ) as output_file:
                run(
                    ["terraform", "show", "-json", TERRAFORM_PLAN_BINARY_FILENAME],
                    cwd=self.__get_cluster_path(),
                    stdout=output_file,
                    check=True,
                )
        except CalledProcessError:
            logging.error("Could not generate plan.")
        finally:
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

        def terraform_apply():
            try:
                destroy = self.get_plan_type() == PlanType.DESTROY
                with open(
                    self.__get_cluster_path(TERRAFORM_APPLY_LOG_FILENAME), "w"
                ) as output_file:
                    environment_variables = environ.copy()
                    if destroy:
                        environment_variables["TF_WARN_OUTPUT_ERRORS"] = "1"
                    run(
                        [
                            "terraform",
                            "apply",
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
                if destroy:
                    rmtree(self.__get_cluster_path())
                else:
                    self.__update_status(ClusterStatusCode.BUILD_SUCCESS)
            except CalledProcessError:
                logging.info("terraform apply returned an error")
                self.__update_status(
                    ClusterStatusCode.DESTROY_ERROR
                    if destroy
                    else ClusterStatusCode.BUILD_ERROR
                )
            finally:
                self.__remove_existing_plan()

        terraform_apply_thread = Thread(target=terraform_apply)
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
