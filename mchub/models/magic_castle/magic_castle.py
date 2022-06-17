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
from sqlalchemy.exc import IntegrityError

from mchub.models.cloud.cloud_manager import CloudManager

from .magic_castle_configuration import MagicCastleConfiguration
from .cluster_status_code import ClusterStatusCode
from .plan_type import PlanType

from ..terraform.terraform_state import TerraformState
from ..terraform.terraform_plan_parser import TerraformPlanParser
from ..cloud.dns_manager import DnsManager
from ..cloud.project import Project
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
TERRAFORM_APPLY_LOG_FILENAME = "terraform_apply.log"
TERRAFORM_PLAN_LOG_FILENAME = "terraform_plan.log"


def terraform_apply(cluster_id, env, main_path, destroy):
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
        logging.error(f"An error occurred while running terraform apply: {err}")
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
        # Remove plan
        if destroy:
            rmtree(main_path, ignore_errors=True)
        else:
            remove(path.join(main_path, TERRAFORM_PLAN_BINARY_FILENAME))

        # Retrieve terraform state
        try:
            with open(
                path.join(main_path, TERRAFORM_STATE_FILENAME), "r"
            ) as tf_state_file:
                tf_state = TerraformState(json.load(tf_state_file))
        except (FileNotFoundError, json.decoder.JSONDecodeError):
            tf_state = None

        # Save results in database
        from ... import create_app

        with create_app().app_context():
            orm = MagicCastleORM.query.get(cluster_id)
            if destroy:
                db.session.delete(orm)
            else:
                orm.plan_type = PlanType.NONE
                orm.plan = None
                orm.status = status
                orm.tf_state = tf_state
                orm.applied_config = orm.config
            db.session.commit()


class MagicCastleORM(db.Model):
    __tablename__ = "magiccastle"
    id = db.Column(db.Integer, primary_key=True)
    hostname = db.Column(db.String(256), unique=True, nullable=False)
    status = db.Column(db.Enum(ClusterStatusCode), default=ClusterStatusCode.NOT_FOUND)
    plan_type = db.Column(db.Enum(PlanType), default=PlanType.NONE)
    created = db.Column(db.DateTime(), default=func.now())
    expiration_date = db.Column(db.String(32))
    config = db.Column(db.PickleType())
    applied_config = db.Column(db.PickleType())
    tf_state = db.Column(db.PickleType())
    plan = db.Column(db.PickleType())
    project_id = db.Column(db.Integer, db.ForeignKey("project.id"))
    project = db.relationship("Project", back_populates="magic_castles", uselist=False)


class MagicCastle:
    """
    Magic Castle is the class that manages everything related to the state of a Magic Castle cluster.
    It is responsible for building, modifying and destroying the cluster using Terraform.
    It is also used to get the state of the cluster and the cloud resources available.

    Note: In this class, the database connection is recreated everytime the database must be accessed
    to avoid using the same connection in multiple threads (which doesn't work with sqlite).
    """

    __slots__ = ["orm"]

    def __init__(self, orm=None):
        if orm:
            self.orm = orm
        else:
            self.orm = MagicCastleORM(
                status=ClusterStatusCode.NOT_FOUND,
                plan_type=PlanType.NONE,
                config={},
            )

    @property
    def hostname(self):
        return self.orm.hostname

    @property
    def domain(self):
        return self.config.domain

    @property
    def path(self):
        return path.join(CLUSTERS_PATH, self.hostname)

    @property
    def main_file(self):
        return path.join(self.path, MAIN_TERRAFORM_FILENAME)

    @property
    def cloud_id(self):
        return self.orm.project.id

    @property
    def project(self):
        return self.orm.project

    @property
    def expiration_date(self):
        return self.orm.expiration_date

    @property
    def age(self):
        now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        delta = now - self.orm.created
        return humanize.naturaldelta(delta)

    @property
    def config(self):
        return self.orm.config

    @config.setter
    def config(self, value):
        self.orm.config = value

    @property
    def applied_config(self):
        return self.orm.applied_config

    def set_configuration(self, configuration: dict):
        expect_tf_changes = False
        self.orm.expiration_date = configuration.pop("expiration_date", None)
        cloud_id = configuration.pop("cloud")["id"]

        if self.orm.project is None or self.orm.project.id != cloud_id:
            self.orm.project = Project.query.get(cloud_id)
            expect_tf_changes = True
        try:
            config = MagicCastleConfiguration(self.orm.project.provider, configuration)
        except ValidationError as err:
            raise InvalidUsageException(
                f"The magic castle configuration could not be parsed.\nError: {err.messages}"
            )
        if self.config != config:
            self.config = config
            self.orm.hostname = f"{self.config.cluster_name}.{self.config.domain}"
            expect_tf_changes = True
        return expect_tf_changes

    @property
    def status(self) -> ClusterStatusCode:
        if self.orm.status == ClusterStatusCode.PROVISIONING_RUNNING:
            now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
            if ProvisioningManager.check_online(self.hostname):
                self.status = ClusterStatusCode.PROVISIONING_SUCCESS
            elif MAX_PROVISIONING_TIME < (now - self.orm.created).total_seconds():
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
                    "status": self.orm.status,
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

    @property
    def plan(self) -> dict:
        return self.orm.plan

    @plan.setter
    def plan(self, plan: dict):
        self.orm.plan = plan

    def get_progress(self):
        if self.plan is None:
            return None

        try:
            with open(path.join(self.path, TERRAFORM_APPLY_LOG_FILENAME), "r") as file:
                terraform_output = file.read()
        except FileNotFoundError:
            # terraform apply was not launched yet, therefore the log file does not exist
            terraform_output = ""
        return TerraformPlanParser.get_done_changes(self.plan, terraform_output)

    @property
    def state(self):
        return {
            **(self.applied_config if self.applied_config else self.config),
            "hostname": self.hostname,
            "status": self.status,
            "freeipa_passwd": self.freeipa_passwd,
            "age": self.age,
            "expiration_date": self.expiration_date,
            "cloud": {"name": self.project.name, "id": self.project.id},
        }

    @property
    def tf_state(self):
        return self.orm.tf_state

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

    def plan_creation(self, data):
        self.set_configuration(data)
        self.plan_type = PlanType.BUILD
        db.session.add(self.orm)
        try:
            db.session.commit()
        except IntegrityError:
            raise ClusterExistsException

        # Create cluster folder on the filesystem
        try:
            mkdir(self.path)
        except Exception as error:
            self.delete()
            raise PlanException(
                "Could not create cluster folder on the filesystem.",
                additional_details=f"hostname: {self.hostname}, error: {error}",
            )

        if MAGIC_CASTLE_PATH[:3] != "git":
            symlink(
                path.join(MAGIC_CASTLE_PATH, self.project.provider),
                path.join(self.path, self.project.provider),
            )
            symlink(
                path.join(MAGIC_CASTLE_PATH, "dns"),
                path.join(self.path, "dns"),
            )

        # Write the main terraform file
        try:
            self.config.write(self.main_file)
        except Exception as error:
            self.delete()
            raise PlanException(
                "Could not write main.tf.json on the filesystem.",
                additional_details=f"hostname: {self.hostname}, error: {error}",
            )

        # Initialize terraform modules
        try:
            run(
                ["terraform", "init", "-no-color", "-input=false"],
                cwd=self.path,
                capture_output=True,
                check=True,
            )
        except Exception as error:
            self.delete()
            raise PlanException(
                "Could not initialize Terraform modules.",
                additional_details=f"hostname: {self.hostname}, error: {error}",
            )

        self.status = ClusterStatusCode.CREATED
        self.create_plan()

    def plan_modification(self, data):
        if not self.found:
            raise ClusterNotFoundException
        if self.is_busy:
            raise BusyClusterException

        config_changed = self.set_configuration(data)
        prev_plan_type = self.plan_type
        self.plan_type = PlanType.BUILD
        db.session.commit()

        # Check if main_file has changed before writing
        # and planning a change, some modifications may
        # only be reflected in the database and do not
        # require a plan.
        if config_changed:
            self.config.write(self.main_file)

        if (
            config_changed
            or self.status
            in (
                ClusterStatusCode.PLAN_ERROR,
                ClusterStatusCode.BUILD_ERROR,
            )
            or prev_plan_type != PlanType.BUILD
        ):
            self.remove_existing_plan()
            self.rotate_terraform_logs(apply=False)
            self.create_plan()

    def plan_destruction(self):
        if self.is_busy:
            raise BusyClusterException

        self.plan_type = PlanType.DESTROY
        if self.tf_state is not None:
            self.remove_existing_plan()
            self.rotate_terraform_logs(apply=False)
            self.create_plan()
        else:
            self.delete()

    def create_plan(self):
        destroy = self.plan_type == PlanType.DESTROY
        self.status = ClusterStatusCode.PLAN_RUNNING

        environment_variables = environ.copy()
        dns_manager = DnsManager(self.domain)
        environment_variables.update(dns_manager.get_environment_variables())
        environment_variables.update(self.project.env)
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
            self.status = ClusterStatusCode.PLAN_ERROR
            with open(plan_log, "r") as input_file:
                log = input_file.read()
            raise PlanException(
                "An error occurred while planning changes.",
                additional_details=f"hostname: {self.hostname}\nlog: {log}",
            )
        except BaseException as err:
            self.status = ClusterStatusCode.PLAN_ERROR
            raise PlanException(
                "An error occurred while planning changes.",
                additional_details=f"hostname: {self.hostname}\nerror: {err}",
            )

        try:
            proc = run(
                [
                    "terraform",
                    "show",
                    "-no-color",
                    "-json",
                    path.join(self.path, TERRAFORM_PLAN_BINARY_FILENAME),
                ],
                cwd=self.path,
                capture_output=True,
                check=True,
            )
        except CalledProcessError:
            self.status = ClusterStatusCode.PLAN_ERROR
            raise PlanException(
                "An error occurred while exporting planned changes.",
                additional_details=f"hostname: {self.hostname}",
            )
        except BaseException as err:
            self.status = ClusterStatusCode.PLAN_ERROR
            raise PlanException(
                "An error occurred while exporting planned changes.",
                additional_details=f"hostname: {self.hostname}\nerror: {err}",
            )

        try:
            self.plan = json.loads(proc.stdout)
        except json.JSONDecodeError:
            self.status = ClusterStatusCode.PLAN_ERROR
            raise PlanException(
                "An error occurred while parsing planned changes.",
                additional_details=f"hostname: {self.hostname}",
            )
        except BaseException as err:
            self.status = ClusterStatusCode.PLAN_ERROR
            raise PlanException(
                "An error occurred while parsing planned changes.",
                additional_details=f"hostname: {self.hostname}\nerror: {err}",
            )

        if self.tf_state:
            self.status = ClusterStatusCode.PROVISIONING_RUNNING
        else:
            self.status = ClusterStatusCode.CREATED
        db.session.commit()

    def apply(self):
        if self.plan is None or not path.exists(
            path.join(self.path, TERRAFORM_PLAN_BINARY_FILENAME)
        ):
            raise PlanNotCreatedException
        if self.is_busy:
            raise BusyClusterException

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
        env.update(self.project.env)
        env.update(DnsManager(self.domain).get_environment_variables())

        self.rotate_terraform_logs(apply=True)
        Thread(
            target=terraform_apply, args=[self.orm.id, env, self.path, destroy]
        ).start()

    def delete(self):
        # Removes the content of the cluster's folder, even if not empty
        rmtree(self.path, ignore_errors=True)
        db.session.delete(self.orm)
        db.session.commit()

    def remove_existing_plan(self):
        try:
            # Remove existing plan, if it exists
            remove(path.join(self.path, TERRAFORM_PLAN_BINARY_FILENAME))
        except FileNotFoundError:
            # Must be a new cluster, without existing plans
            pass
