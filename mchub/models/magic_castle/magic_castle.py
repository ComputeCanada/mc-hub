import datetime
import json
import logging

import humanize

from os import path, environ, mkdir, remove, scandir, rename
from subprocess import run, CalledProcessError
from shutil import rmtree
from threading import Thread

from marshmallow import ValidationError

from . magic_castle_configuration import MagicCastleConfiguration
from . cluster_status_code import ClusterStatusCode
from . plan_type import PlanType

from .. terraform.terraform_state_parser import TerraformStateParser
from .. terraform.terraform_plan_parser import TerraformPlanParser
from .. cloud.dns_manager import DnsManager
from .. puppet.provisioning_manager import ProvisioningManager, MAX_PROVISIONING_TIME

from ... configuration.magic_castle import (
    MAIN_TERRAFORM_FILENAME,
    TERRAFORM_STATE_FILENAME,
)
from ... configuration.env import CLUSTERS_PATH

from ... exceptions.invalid_usage_exception import *
from ... exceptions.server_exception import *

from ... database.database_manager import DatabaseManager


TERRAFORM_PLAN_BINARY_FILENAME = "terraform_plan"
TERRAFORM_PLAN_JSON_FILENAME = "terraform_plan.json"

TERRAFORM_APPLY_LOG_FILENAME = "terraform_apply.log"
TERRAFORM_PLAN_LOG_FILENAME = "terraform_plan.log"


class Owner:
    def __init__(self, id=None):
        self.id = id
        if self.id:
            self.username = self.id.split("@")[0]
        else:
            self.username = None


class MagicCastle:
    """
    Magic Castle is the class that manages everything related to the state of a Magic Castle cluster.
    It is responsible for building, modifying and destroying the cluster using Terraform.
    It is also used to get the state of the cluster and the cloud resources available.

    Note: In this class, the database connection is recreated everytime the database must be accessed
    to avoid using the same connection in multiple threads (which doesn't work with sqlite).
    """

    _status = None
    _owner = None
    _configuration = None
    __plan_type = None
    created = None
    _path = None
    _main_file = None
    expiration_date = None
    cloud_id = None

    def __init__(self, hostname=None, owner=None):
        self.hostname = hostname
        if self.read_db_entry():
            if owner is not None and self.owner.id != owner:
                raise ClusterNotFoundException
            if self._main_file and path.exists(self._main_file):
                self._configuration = MagicCastleConfiguration.get_from_main_file(
                    self._main_file
                )
        else:
            self._owner = Owner(owner)

    @property
    def hostname(self):
        return f"{self.cluster_name}.{self.domain}"

    @hostname.setter
    def hostname(self, value):

        if value is not None:
            self.cluster_name, self.domain = value.split(".", 1)
            self._path = path.join(CLUSTERS_PATH, self.hostname)
            self._main_file = path.join(self._path, MAIN_TERRAFORM_FILENAME)
        else:
            self.cluster_name, self.domain = None, None
            self._path = None
            self._main_file = None

    @property
    def owner(self):
        if self._owner is None:
            self.read_db_entry()
        return self._owner

    @property
    def age(self):
        if self.created is None:
            self.read_db_entry()
        delta = datetime.datetime.now() - self.created
        return humanize.naturaldelta(delta)

    def set_configuration(self, configuration: dict):
        self.expiration_date = configuration.pop("expiration_date", None)
        self.cloud_id = configuration.pop("cloud_id")
        try:
            self._configuration = MagicCastleConfiguration(configuration)
        except ValidationError:
            raise InvalidUsageException(
                "The magic castle configuration could not be parsed."
            )
        self.hostname = (
            f"{self._configuration.cluster_name}.{self._configuration.domain}"
        )

    def read_db_entry(self):
        with DatabaseManager.connect() as database_connection:
            result = database_connection.execute(
                "SELECT status, owner, created, plan_type, expiration_date, cloud_id FROM magic_castles WHERE hostname = ?",
                (self.hostname,),
            ).fetchone()
            if result:
                self._status = ClusterStatusCode(result[0])
                self._owner = Owner(result[1])
                self.created = result[2]
                self.__plan_type = PlanType(result[3])
                self.expiration_date = result[4]
                self.cloud_id = result[5]
            else:
                self._status = ClusterStatusCode.NOT_FOUND
                self.__plan_type = PlanType.NONE
                self._owner = Owner(None)
            return bool(result)

    @property
    def status(self) -> ClusterStatusCode:
        if self._status is None:
            self.read_db_entry()

        if self._status == ClusterStatusCode.PROVISIONING_RUNNING:
            if ProvisioningManager(self.hostname).check_online():
                self.status = ClusterStatusCode.PROVISIONING_SUCCESS
            elif MAX_PROVISIONING_TIME < (datetime.datetime.now() - self.created).total_seconds() :
                self.status = ClusterStatusCode.PROVISIONING_ERROR

        return self._status

    @status.setter
    def status(self, status: ClusterStatusCode):
        self._status = status
        with DatabaseManager.connect() as database_connection:
            database_connection.execute(
                "UPDATE magic_castles SET status = ? WHERE hostname = ?",
                (self._status.value, self.hostname),
            )
            database_connection.commit()

        # Log cluster status updates for log analytics
        print(
            json.dumps(
                {
                    "hostname": self.hostname,
                    "status": self._status.value,
                    "owner": self.owner.id,
                }
            ),
            flush=True,
        )

    def __rotate_terraform_logs(self, *, apply: bool):
        """
        Rotates filenames for logs generated by running `terraform plan` or `terraform apply`.

        For instance, it will rename an existing file named terraform_plan.log to terraform_plan.log.1.
        Any log file already ending with a number will have its number incremented by one
        (e.g.  terraform_plan.log.1 would be renamed to terraform_plan.log.2).

        :param apply: True to rotate logs of `terraform apply`, False to rotate logs of `terraform plan`.
        """
        if apply:
            base_file_name = TERRAFORM_APPLY_LOG_FILENAME
        else:
            base_file_name = TERRAFORM_PLAN_LOG_FILENAME

        logs_path = path.join(CLUSTERS_PATH, self.hostname)
        old_file_names = []
        with scandir(logs_path) as it:
            for entry in it:
                if entry.is_file() and entry.name.startswith(base_file_name):
                    old_file_names.append(entry.name)

        # Sort alphabetically to always rename the log file with the highest index first
        old_file_names.sort(reverse=True)
        for old_file_name in old_file_names:
            if old_file_name == base_file_name:
                # terraform_apply.log becomes terraform_apply.log.1
                new_file_index = 1
            else:
                # terraform_apply.log.1 becomes terraform_apply.log.2 and so on
                new_file_index = int(old_file_name.split(".")[-1]) + 1
            new_file_name = f"{base_file_name}.{new_file_index}"
            rename(
                path.join(self._path, old_file_name),
                path.join(self._path, new_file_name),
            )

    def get_plan_type(self) -> PlanType:
        if self.__plan_type is None:
            self.read_db_entry()
        return self.__plan_type

    def __update_plan_type(self, plan_type: PlanType):
        self.__plan_type = plan_type
        with DatabaseManager.connect() as database_connection:
            database_connection.execute(
                "UPDATE magic_castles SET plan_type = ? WHERE hostname = ?",
                (self.__plan_type.value, self.hostname),
            )
            database_connection.commit()

    def get_progress(self):
        if not self.found:
            raise ClusterNotFoundException

        initial_plan = self.__get_plan()
        if initial_plan is None:
            return None
        try:
            with open(path.join(self._path, TERRAFORM_APPLY_LOG_FILENAME), "r") as file:
                terraform_output = file.read()
        except FileNotFoundError:
            # terraform apply was not launched yet, therefore the log file does not exist
            terraform_output = ""
        return TerraformPlanParser.get_done_changes(initial_plan, terraform_output)

    def dump_configuration(self):
        """
        Returns the Magic Castle configuration dictionary of the current cluster.

        :return: The configuration dictionary
        """
        if not self.found:
            raise ClusterNotFoundException

        if self._configuration:
            return self._configuration.to_dict()
        else:
            return {}

    def dump_state(self):
        return {
            **self.dump_configuration(),
            "hostname": self.hostname,
            "status": self.status.value,
            "freeipa_passwd": self.get_freeipa_passwd(),
            "owner": self.owner.username,
            "age": self.age,
            "expiration_date": self.expiration_date,
            "cloud_id": self.cloud_id,
        }

    def get_freeipa_passwd(self):
        if self.is_busy:
            return None

        try:
            with open(
                path.join(self._path, TERRAFORM_STATE_FILENAME), "r"
            ) as terraform_state_file:
                state = json.load(terraform_state_file)
                return TerraformStateParser(state).get_freeipa_passwd()
        except FileNotFoundError:
            return None

    def get_allocated_resources(self):
        if self.is_busy:
            raise BusyClusterException

        allocated_resources = dict(
            pre_allocated_instance_count=0,
            pre_allocated_ram=0,
            pre_allocated_cores=0,
            pre_allocated_volume_count=0,
            pre_allocated_volume_size=0,
        )

        if self._path:
            try:
                with open(
                    path.join(self._path, TERRAFORM_STATE_FILENAME), "r"
                ) as terraform_state_file:
                    state = json.load(terraform_state_file)
            except FileNotFoundError:
                pass
            else:
                parser = TerraformStateParser(state)
                allocated_resources = dict(
                    pre_allocated_instance_count=parser.get_instance_count(),
                    pre_allocated_ram=parser.get_ram(),
                    pre_allocated_cores=parser.get_cores(),
                    pre_allocated_volume_count=parser.get_volume_count(),
                    pre_allocated_volume_size=parser.get_volume_size(),
                )

        return allocated_resources

    @property
    def is_busy(self):
        return self.status in [
            ClusterStatusCode.PLAN_RUNNING,
            ClusterStatusCode.BUILD_RUNNING,
            ClusterStatusCode.DESTROY_RUNNING,
        ]

    @property
    def found(self):
        return self.status != ClusterStatusCode.NOT_FOUND

    @property
    def plan_created(self):
        return self.status != ClusterStatusCode.PLAN_RUNNING and path.exists(
            path.join(self._path, TERRAFORM_PLAN_BINARY_FILENAME)
        )

    def plan_creation(self, data):
        if self.found:
            raise ClusterExistsException
        self.set_configuration(data)

        with DatabaseManager.connect() as database_connection:
            database_connection.execute(
                "INSERT INTO magic_castles (hostname, status, plan_type, owner, expiration_date, cloud_id) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    self.hostname,
                    ClusterStatusCode.CREATED.value,
                    PlanType.BUILD.value,
                    self.owner.id,
                    self.expiration_date,
                    self.cloud_id,
                ),
            )
            database_connection.commit()

        self.__plan(destroy=False, existing_cluster=False)

    def plan_modification(self, data):
        if not self.found:
            raise ClusterNotFoundException
        if self.is_busy:
            raise BusyClusterException
        self.set_configuration(data)

        with DatabaseManager.connect() as database_connection:
            database_connection.execute(
                "UPDATE magic_castles SET expiration_date = ? WHERE hostname = ?",
                (self.expiration_date, self.hostname),
            )
            database_connection.commit()

        self.__plan(destroy=False, existing_cluster=True)

    def plan_destruction(self):
        if not self.found:
            raise ClusterNotFoundException
        if self.is_busy:
            raise BusyClusterException

        self.__plan(destroy=True, existing_cluster=True)

    def __plan(self, *, destroy, existing_cluster):
        if existing_cluster:
            self.__remove_existing_plan()
            previous_status = self.status
        else:
            mkdir(self._path)
            previous_status = ClusterStatusCode.CREATED

        if destroy:
            plan_type = PlanType.DESTROY
        else:
            plan_type = PlanType.BUILD
            self._configuration.update_main_file(self._main_file)

        if destroy and self.status == ClusterStatusCode.CREATED:
            self.delete()
            return

        self.status = ClusterStatusCode.PLAN_RUNNING
        self.__update_plan_type(plan_type)

        if not existing_cluster:
            try:
                run(
                    ["terraform", "init", "-no-color", "-input=false"],
                    cwd=self._path,
                    capture_output=True,
                    check=True,
                )
            except CalledProcessError:
                self.status = previous_status
                raise PlanException(
                    "An error occurred while initializing Terraform.",
                    additional_details=f"hostname: {self.hostname}",
                )

        self.__rotate_terraform_logs(apply=False)
        environment_variables = environ.copy()
        dns_manager = DnsManager(self.domain)
        environment_variables.update(dns_manager.get_environment_variables())
        environment_variables["OS_CLOUD"] = self.cloud_id
        plan_log = path.join(self._path, TERRAFORM_PLAN_LOG_FILENAME)
        try:
            with open(plan_log, "w") as output_file:
                run(
                    [
                        "terraform",
                        "plan",
                        "-input=false",
                        "-no-color",
                        "-refresh=" + ("true" if destroy else "false"),
                        "-destroy=" + ("true" if destroy else "false"),
                        "-out=" + path.join(self._path, TERRAFORM_PLAN_BINARY_FILENAME),
                    ],
                    cwd=self._path,
                    env=environment_variables,
                    stdout=output_file,
                    stderr=output_file,
                    check=True,
                )
        except CalledProcessError:
            self.status = previous_status
            raise PlanException(
                "An error occurred while planning changes.",
                additional_details=f"hostname: {self.hostname}",
            )

        plan_json_path = path.join(self._path, TERRAFORM_PLAN_JSON_FILENAME)
        try:
            with open(plan_json_path, "w") as output_file:
                run(
                    [
                        "terraform",
                        "show",
                        "-no-color",
                        "-json",
                        path.join(self._path, TERRAFORM_PLAN_BINARY_FILENAME),
                    ],
                    cwd=self._path,
                    stdout=output_file,
                    check=True,
                )
        except CalledProcessError:
            self.status = previous_status
            raise PlanException(
                "An error occurred while exporting planned changes.",
                additional_details=f"hostname: {self.hostname}",
            )

        self.status = previous_status

    def apply(self):
        if not self.found:
            raise ClusterNotFoundException
        if self.is_busy:
            raise BusyClusterException
        if not self.plan_created:
            raise PlanNotCreatedException

        plan_type = self.get_plan_type()
        if plan_type == PlanType.BUILD:
            self.status = ClusterStatusCode.BUILD_RUNNING
            destroy = False
        elif plan_type == PlanType.DESTROY:
            self.status = ClusterStatusCode.DESTROY_RUNNING
            destroy = True
        else:
            raise PlanNotCreatedException

        def terraform_apply():
            self.__rotate_terraform_logs(apply=True)
            env = environ.copy()
            env["OS_CLOUD"] = self.cloud_id
            env.update(DnsManager(self.domain).get_environment_variables())
            if destroy:
                env["TF_WARN_OUTPUT_ERRORS"] = "1"
            try:
                with open(
                    path.join(self._path, TERRAFORM_APPLY_LOG_FILENAME), "w"
                ) as output_file:
                    run(
                        [
                            "terraform",
                            "apply",
                            "-input=false",
                            "-no-color",
                            "-auto-approve",
                            path.join(self._path, TERRAFORM_PLAN_BINARY_FILENAME),
                        ],
                        cwd=self._path,
                        stdout=output_file,
                        stderr=output_file,
                        check=True,
                        env=env,
                    )
            except CalledProcessError:
                logging.info("An error occurred while running terraform apply.")
                if destroy:
                    self.status = ClusterStatusCode.DESTROY_ERROR
                else:
                    self.status = ClusterStatusCode.BUILD_ERROR
            else:
                if destroy:
                    self.delete()
                else:
                    self.status = ClusterStatusCode.PROVISIONING_RUNNING
            finally:
                self.__remove_existing_plan()

        Thread(
            target=terraform_apply,
        ).start()

    def delete(self):
        # Removes the content of the cluster's folder, even if not empty
        rmtree(self._path, ignore_errors=True)
        with DatabaseManager.connect() as database_connection:
            database_connection.execute(
                "DELETE FROM magic_castles WHERE hostname = ?",
                (self.hostname,),
            )
            database_connection.commit()

    def __remove_existing_plan(self):
        self.__update_plan_type(PlanType.NONE)
        try:
            # Remove existing plan, if it exists
            remove(path.join(self._path, TERRAFORM_PLAN_BINARY_FILENAME))
            remove(path.join(self._path, TERRAFORM_PLAN_JSON_FILENAME))
        except FileNotFoundError:
            # Must be a new cluster, without existing plans
            pass

    def __get_plan(self):
        try:
            with open(
                path.join(self._path, TERRAFORM_PLAN_JSON_FILENAME), "r"
            ) as plan_file:
                return json.load(plan_file)
        except (FileNotFoundError, json.decoder.JSONDecodeError):
            return None
