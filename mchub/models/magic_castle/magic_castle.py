import datetime
import json
import logging

import humanize

from os import path, environ, mkdir, remove, scandir, rename, symlink
from subprocess import run, CalledProcessError
from shutil import rmtree
from threading import Thread

from marshmallow import ValidationError
from sqlalchemy.sql import func

from .magic_castle_configuration import MagicCastleConfiguration
from .cluster_status_code import ClusterStatusCode
from .plan_type import PlanType

from ..terraform.terraform_state_parser import TerraformStateParser
from ..terraform.terraform_plan_parser import TerraformPlanParser
from ..cloud.dns_manager import DnsManager
from ..puppet.provisioning_manager import ProvisioningManager, MAX_PROVISIONING_TIME

from ...configuration.magic_castle import (
    MAIN_TERRAFORM_FILENAME,
    TERRAFORM_STATE_FILENAME,
    MAGIC_CASTLE_PATH,
)
from ...configuration.env import CLUSTERS_PATH

from ...exceptions.invalid_usage_exception import *
from ...exceptions.server_exception import *

from ...database import db


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


def terraform_apply(hostname, env, main_path, destroy):
    log_path = path.join(main_path, TERRAFORM_APPLY_LOG_FILENAME)
    plan_path = path.join(main_path, TERRAFORM_PLAN_BINARY_FILENAME)
    try:
        with open(log_path, "w") as output_file:
            run(
                [
                    "terraform",
                    "apply",
                    "-input=false",
                    "-no-color",
                    "-auto-approve",
                    plan_path,
                ],
                cwd=main_path,
                stdout=output_file,
                stderr=output_file,
                check=True,
                env=env,
            )
    except CalledProcessError as err:
        logging.info(f"An error occurred while running terraform apply: {err}")
        if destroy:
            status = ClusterStatusCode.DESTROY_ERROR
        else:
            status = ClusterStatusCode.BUILD_ERROR
        # Disable removal from database
        destroy = False
    else:
        if not destroy:
            status = ClusterStatusCode.PROVISIONING_RUNNING
    finally:
        # Remove plans
        from ... import create_app

        with create_app().app_context():
            orm = MagicCastleORM.query.filter_by(hostname=hostname).first()
            if destroy:
                rmtree(main_path, ignore_errors=True)
                db.session.delete(orm)
            else:
                remove(path.join(main_path, TERRAFORM_PLAN_BINARY_FILENAME))
                remove(path.join(main_path, TERRAFORM_PLAN_JSON_FILENAME))
                orm.plan_type = PlanType.NONE
                orm.status = status
            db.session.commit()


class MagicCastleORM(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hostname = db.Column(db.String(256), unique=True, nullable=False)
    status = db.Column(db.Enum(ClusterStatusCode), default=ClusterStatusCode.NOT_FOUND)
    plan_type = db.Column(db.Enum(PlanType), default=PlanType.NONE)
    owner = db.Column(db.String(64))
    created = db.Column(db.DateTime(), default=func.now())
    expiration_date = db.Column(db.String(32))
    cloud_id = db.Column(db.String(128))


class MagicCastle:
    """
    Magic Castle is the class that manages everything related to the state of a Magic Castle cluster.
    It is responsible for building, modifying and destroying the cluster using Terraform.
    It is also used to get the state of the cluster and the cloud resources available.

    Note: In this class, the database connection is recreated everytime the database must be accessed
    to avoid using the same connection in multiple threads (which doesn't work with sqlite).
    """

    _owner = None
    _configuration = None
    _tf_state = None

    def __init__(self, orm=None, hostname=None, owner=None):
        if orm:
            self.orm = orm
            self._owner = Owner(orm.owner)
            self.hostname = orm.hostname
            if path.exists(self.main_file):
                self._configuration = MagicCastleConfiguration.get_from_main_file(
                    self.main_file
                )
        else:
            self.orm = MagicCastleORM(
                hostname=hostname,
                owner=owner,
                status=ClusterStatusCode.NOT_FOUND,
                plan_type=PlanType.NONE,
            )
            self._owner = Owner(owner)
            self.hostname = hostname

    @property
    def hostname(self):
        return self.orm.hostname

    @hostname.setter
    def hostname(self, value):
        if value is not None:
            self.cluster_name, self.domain = value.split(".", 1)
            self.orm.hostname = f"{self.cluster_name}.{self.domain}"
        else:
            self.cluster_name = None
            self.domain = None

    @property
    def path(self):
        return path.join(CLUSTERS_PATH, self.hostname)

    @property
    def main_file(self):
        return path.join(self.path, MAIN_TERRAFORM_FILENAME)

    @property
    def cloud_id(self):
        return self.orm.cloud_id

    @property
    def expiration_date(self):
        return self.orm.expiration_date

    @property
    def owner(self):
        return self._owner

    @property
    def age(self):
        delta = datetime.datetime.now() - self.orm.created
        return humanize.naturaldelta(delta)

    def set_configuration(self, configuration: dict):
        self.orm.expiration_date = configuration.pop("expiration_date", None)
        self.orm.cloud_id = configuration.pop("cloud_id")
        try:
            self._configuration = MagicCastleConfiguration(configuration)
        except ValidationError:
            raise InvalidUsageException(
                "The magic castle configuration could not be parsed."
            )
        self.hostname = (
            f"{self._configuration.cluster_name}.{self._configuration.domain}"
        )

    @property
    def status(self) -> ClusterStatusCode:
        if self.orm.status == ClusterStatusCode.PROVISIONING_RUNNING:
            if ProvisioningManager.check_online(self.hostname):
                self.status = ClusterStatusCode.PROVISIONING_SUCCESS
            elif (
                MAX_PROVISIONING_TIME
                < (datetime.datetime.now() - self.orm.created).total_seconds()
            ):
                self.status = ClusterStatusCode.PROVISIONING_ERROR

        return self.orm.status

    @status.setter
    def status(self, status: ClusterStatusCode):
        self.orm.status = status
        db.session.commit()

        # Log cluster status updates for log analytics
        print(
            json.dumps(
                {
                    "hostname": self.hostname,
                    "status": self.orm.status.value,
                    "owner": self.owner.id,
                }
            ),
            flush=True,
        )

    def rotate_terraform_logs(self, *, apply: bool):
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
                path.join(self.path, old_file_name),
                path.join(self.path, new_file_name),
            )

    @property
    def plan_type(self) -> PlanType:
        return self.orm.plan_type

    @plan_type.setter
    def plan_type(self, plan_type: PlanType):
        self.orm.plan_type = plan_type

    def get_progress(self):
        if not self.found:
            raise ClusterNotFoundException

        initial_plan = self.load_plan()
        if initial_plan is None:
            return None
        try:
            with open(path.join(self.path, TERRAFORM_APPLY_LOG_FILENAME), "r") as file:
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
            "freeipa_passwd": self.freeipa_passwd,
            "owner": self.owner.username,
            "age": self.age,
            "expiration_date": self.expiration_date,
            "cloud_id": self.cloud_id,
        }

    @property
    def freeipa_passwd(self):
        if self.tf_state is not None:
            return self.tf_state.freeipa_passwd
        else:
            return None

    @property
    def allocated_resources(self):
        if self.is_busy:
            raise BusyClusterException

        if self.tf_state is not None:
            return dict(
                pre_allocated_instance_count=self.tf_state.instance_count,
                pre_allocated_ram=self.tf_state.ram,
                pre_allocated_cores=self.tf_state.cores,
                pre_allocated_volume_count=self.tf_state.volume_count,
                pre_allocated_volume_size=self.tf_state.volume_size,
            )
        else:
            return dict(
                pre_allocated_instance_count=0,
                pre_allocated_ram=0,
                pre_allocated_cores=0,
                pre_allocated_volume_count=0,
                pre_allocated_volume_size=0,
            )

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
            path.join(self.path, TERRAFORM_PLAN_BINARY_FILENAME)
        )

    def plan_creation(self, data):
        if self.found:
            raise ClusterExistsException
        self.set_configuration(data)
        self.status = ClusterStatusCode.CREATED
        self.plan_type = PlanType.BUILD

        self.__plan(destroy=False, existing_cluster=False)

        db.session.add(self.orm)
        db.session.commit()

    def plan_modification(self, data):
        if not self.found:
            raise ClusterNotFoundException
        if self.is_busy:
            raise BusyClusterException
        self.set_configuration(data)
        db.session.commit()

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
            mkdir(self.path)
            if MAGIC_CASTLE_PATH[:3] != "git":
                symlink(
                    path.join(MAGIC_CASTLE_PATH, "openstack"),
                    path.join(self.path, "openstack"),
                )
                symlink(
                    path.join(MAGIC_CASTLE_PATH, "dns"),
                    path.join(self.path, "dns"),
                )
            previous_status = ClusterStatusCode.CREATED

        if destroy:
            plan_type = PlanType.DESTROY
        else:
            plan_type = PlanType.BUILD
            self._configuration.update_main_file(self.main_file)

        if destroy and self.status == ClusterStatusCode.CREATED:
            self.delete()
            return

        self.status = ClusterStatusCode.PLAN_RUNNING
        self.plan_type = plan_type

        if not existing_cluster:
            try:
                run(
                    ["terraform", "init", "-no-color", "-input=false"],
                    cwd=self.path,
                    capture_output=True,
                    check=True,
                )
            except CalledProcessError:
                self.status = previous_status
                raise PlanException(
                    "An error occurred while initializing Terraform.",
                    additional_details=f"hostname: {self.hostname}",
                )

        self.rotate_terraform_logs(apply=False)
        environment_variables = environ.copy()
        dns_manager = DnsManager(self.domain)
        environment_variables.update(dns_manager.get_environment_variables())
        environment_variables["OS_CLOUD"] = self.cloud_id
        plan_log = path.join(self.path, TERRAFORM_PLAN_LOG_FILENAME)
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
                        "-out=" + path.join(self.path, TERRAFORM_PLAN_BINARY_FILENAME),
                    ],
                    cwd=self.path,
                    env=environment_variables,
                    stdout=output_file,
                    stderr=output_file,
                    check=True,
                )
        except CalledProcessError:
            self.status = previous_status
            with open(plan_log, "r") as input_file:
                log = input_file.read()
            raise PlanException(
                "An error occurred while planning changes.",
                additional_details=f"hostname: {self.hostname}\nlog: {log}",
            )

        plan_json_path = path.join(self.path, TERRAFORM_PLAN_JSON_FILENAME)
        try:
            with open(plan_json_path, "w") as output_file:
                run(
                    [
                        "terraform",
                        "show",
                        "-no-color",
                        "-json",
                        path.join(self.path, TERRAFORM_PLAN_BINARY_FILENAME),
                    ],
                    cwd=self.path,
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

    @property
    def tf_state(self):
        if self._tf_state is None and self.path is not None:
            try:
                with open(
                    path.join(self.path, TERRAFORM_STATE_FILENAME), "r"
                ) as terraform_state_file:
                    state = json.load(terraform_state_file)
            except (FileNotFoundError, json.decoder.JSONDecodeError):
                self._tf_state = None
            else:
                self._tf_state = TerraformStateParser(state)
        return self._tf_state

    def apply(self):
        if not self.found:
            raise ClusterNotFoundException
        if self.is_busy:
            raise BusyClusterException
        if not self.plan_created:
            raise PlanNotCreatedException

        if self.plan_type == PlanType.BUILD:
            self.status = ClusterStatusCode.BUILD_RUNNING
            destroy = False
        elif self.plan_type == PlanType.DESTROY:
            self.status = ClusterStatusCode.DESTROY_RUNNING
            destroy = True
        else:
            raise PlanNotCreatedException

        env = environ.copy()
        if destroy:
            env["TF_WARN_OUTPUT_ERRORS"] = "1"
        env["OS_CLOUD"] = self.orm.cloud_id
        env.update(DnsManager(self.domain).get_environment_variables())

        self.rotate_terraform_logs(apply=True)
        Thread(
            target=terraform_apply, args=[self.hostname, env, self.path, destroy]
        ).start()

    def delete(self):
        # Removes the content of the cluster's folder, even if not empty
        rmtree(self.path, ignore_errors=True)
        db.session.delete(self.orm)
        db.session.commit()

    def __remove_existing_plan(self):
        self.plan_type = PlanType.NONE
        try:
            # Remove existing plan, if it exists
            remove(path.join(self.path, TERRAFORM_PLAN_BINARY_FILENAME))
            remove(path.join(self.path, TERRAFORM_PLAN_JSON_FILENAME))
        except FileNotFoundError:
            # Must be a new cluster, without existing plans
            pass

    def load_plan(self):
        try:
            with open(
                path.join(self.path, TERRAFORM_PLAN_JSON_FILENAME), "r"
            ) as plan_file:
                return json.load(plan_file)
        except (FileNotFoundError, json.decoder.JSONDecodeError):
            return None
