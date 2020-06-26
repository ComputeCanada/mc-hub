from os import path, environ, mkdir, listdir
from os.path import isdir
from flask import render_template
from subprocess import run, CalledProcessError
from shutil import rmtree
from threading import Thread
from marshmallow import ValidationError
from models.cluster_status_code import ClusterStatusCode
from models.magic_castle_schema import MagicCastleSchema
from models.terraform_state_parser import TerraformStateParser
from models.terraform_plan_parser import TerraformPlanParser
from models.openstack_manager import OpenStackManager
from exceptions.invalid_usage_exception import InvalidUsageException
from exceptions.busy_cluster_exception import BusyClusterException
from exceptions.cluster_not_found_exception import ClusterNotFoundException
from exceptions.cluster_exists_exception import ClusterExistsException
import logging
import json

MAGIC_CASTLE_RELEASE_PATH = path.join(
    environ["HOME"], "magic_castle-openstack-" + environ["MAGIC_CASTLE_VERSION"]
)
CLUSTERS_PATH = path.join(environ["HOME"], "clusters")

STATUS_FILENAME = "status.txt"
TERRAFORM_STATE_FILENAME = "terraform.tfstate"
TERRAFORM_PLAN_BINARY_FILENAME = "terraform_plan"
TERRAFORM_PLAN_JSON_FILENAME = "terraform_plan.json"

TERRAFORM_APPLY_LOG_FILENAME = "terraform_apply.log"
TERRAFORM_DESTROY_LOG_FILENAME = "terraform_destroy.log"
TERRAFORM_PLAN_LOG_FILENAME = "terraform_plan.log"


class MagicCastle:
    """
    Magic Castle is the class that manages the state of Magic Castle clusters.
    It is responsible for building, modifying and destroying clusters.
    It is also used to parse the state of existing clusters and return it in
    a simple dictionary format.
    """

    def __init__(self, cluster_name=None):
        self.__configuration = {}
        if cluster_name:
            self.__configuration["cluster_name"] = cluster_name

    @classmethod
    def all(cls):
        """
        Retrieve all the Magic Castles in the clusters folder.
        :return: A list of MagicCastle objects
        """
        return [
            cls(cluster_name)
            for cluster_name in sorted(listdir(CLUSTERS_PATH))
            if isdir(path.join(CLUSTERS_PATH, cluster_name))
        ]

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
        status_file_path = self.__get_cluster_path(STATUS_FILENAME)
        if not status_file_path or not path.exists(status_file_path):
            return ClusterStatusCode.NOT_FOUND
        with open(status_file_path, "r") as status_file:
            return ClusterStatusCode(status_file.read())

    def get_progress(self):
        if self.__not_found():
            raise ClusterNotFoundException

        initial_plan = self.__get_plan()
        if initial_plan is None:
            return None

        terraform_output_filename = (
            TERRAFORM_DESTROY_LOG_FILENAME
            if self.get_status() == ClusterStatusCode.DESTROY_RUNNING
            else TERRAFORM_APPLY_LOG_FILENAME
        )
        with open(self.__get_cluster_path(terraform_output_filename), "r") as file:
            terraform_output = file.read()
        return TerraformPlanParser.get_done_changes(initial_plan, terraform_output)

    def get_state(self):
        if self.__is_busy():
            raise BusyClusterException
        if self.__not_found():
            raise ClusterNotFoundException

        with open(
            self.__get_cluster_path(TERRAFORM_STATE_FILENAME), "r"
        ) as terraform_state_file:
            state = json.load(terraform_state_file)
        parser = TerraformStateParser(self.get_name(), state)
        return MagicCastleSchema().dump(parser.get_state_summary())

    def get_available_resources(self):
        if self.__is_busy():
            raise BusyClusterException

        if self.__found():
            with open(
                self.__get_cluster_path(TERRAFORM_STATE_FILENAME), "r"
            ) as terraform_state_file:
                state = json.load(terraform_state_file)
            parser = TerraformStateParser(self.get_name(), state)

            openstack_manager = OpenStackManager(
                pre_allocated_ram=parser.get_ram(),
                pre_allocated_cores=parser.get_cores(),
                pre_allocated_volume_count=parser.get_volume_count(),
                pre_allocated_volume_size=parser.get_volume_size(),
                pre_allocated_floating_ips=parser.get_os_floating_ips(),
            )
        else:
            openstack_manager = OpenStackManager()

        return openstack_manager.get_available_resources()

    def __is_busy(self):
        return self.get_status() in [
            ClusterStatusCode.BUILD_RUNNING,
            ClusterStatusCode.DESTROY_RUNNING,
        ]

    def __not_found(self):
        return self.get_status() == ClusterStatusCode.NOT_FOUND

    def __found(self):
        return self.get_status() != ClusterStatusCode.NOT_FOUND

    def __get_cluster_path(self, sub_path=""):
        if self.get_name():
            return path.join(CLUSTERS_PATH, self.get_name(), sub_path)
        else:
            return None

    def get_name(self):
        return self.__configuration.get("cluster_name")

    def apply_new(self):
        if self.__found():
            raise ClusterExistsException

        mkdir(self.__get_cluster_path())
        return self.__apply()

    def apply_existing(self):
        if self.__not_found():
            raise ClusterNotFoundException
        if self.__is_busy():
            raise BusyClusterException

        return self.__apply()

    def __apply(self):
        self.__remove_existing_plan()
        self.__update_status(ClusterStatusCode.BUILD_RUNNING)

        with open(self.__get_cluster_path("main.tf"), "w") as cluster_config_file:
            cluster_config_file.write(
                render_template(
                    "main.tf",
                    **self.__configuration,
                    magic_castle_release_path=MAGIC_CASTLE_RELEASE_PATH,
                )
            )

        def terraform_apply():
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
            except CalledProcessError:
                logging.error("terraform init returned an error")
                return

            try:
                self.__generate_plan_file(refresh=True)
                with open(
                    self.__get_cluster_path(TERRAFORM_APPLY_LOG_FILENAME), "w"
                ) as output_file:
                    run(
                        ["terraform", "apply", "-no-color", "-auto-approve"],
                        cwd=self.__get_cluster_path(),
                        stdout=output_file,
                        stderr=output_file,
                        check=True,
                    )
                self.__update_status(ClusterStatusCode.BUILD_SUCCESS)
            except CalledProcessError:
                logging.info("terraform apply returned an error")
                self.__update_status(ClusterStatusCode.BUILD_ERROR)
                return

        build_cluster_thread = Thread(target=terraform_apply)
        build_cluster_thread.start()

    def destroy(self):
        if self.__is_busy():
            raise BusyClusterException
        if self.__not_found():
            raise ClusterNotFoundException

        self.__remove_existing_plan()
        self.__update_status(ClusterStatusCode.DESTROY_RUNNING)

        def terraform_destroy():
            self.__generate_plan_file(refresh=True, destroy=True)
            with open(
                self.__get_cluster_path(TERRAFORM_DESTROY_LOG_FILENAME), "w"
            ) as output_file:
                try:
                    run(
                        ["terraform", "destroy", "-no-color", "-auto-approve",],
                        cwd=self.__get_cluster_path(),
                        stdout=output_file,
                        stderr=output_file,
                        check=True,
                    )
                    rmtree(self.__get_cluster_path())
                except CalledProcessError:
                    logging.info("terraform destroy returned an error")
                    self.__update_status(ClusterStatusCode.DESTROY_ERROR)

        destroy_cluster_thread = Thread(target=terraform_destroy)
        destroy_cluster_thread.start()

    def __remove_existing_plan(self):
        try:
            # Remove existing plan, if it exists
            remove(self.__get_cluster_path(TERRAFORM_PLAN_BINARY_FILENAME))
            remove(self.__get_cluster_path(TERRAFORM_PLAN_JSON_FILENAME))
        except FileNotFoundError:
            # Must be a new cluster, without existing plans
            pass

    def __generate_plan_file(self, *, refresh, destroy=False):
        try:
            with open(
                self.__get_cluster_path(TERRAFORM_PLAN_LOG_FILENAME), "w"
            ) as output_file:
                run(
                    [
                        "terraform",
                        "plan",
                        "-no-color",
                        "-destroy=" + ("true" if destroy else "false"),
                        "-refresh=" + ("true" if refresh else "false"),
                        "-lock=" + ("true" if refresh else "false"),
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
            logging.info("Could not generate plan file.")

    def __get_plan(self):
        try:
            with open(
                self.__get_cluster_path(TERRAFORM_PLAN_JSON_FILENAME), "r"
            ) as plan_file:
                plan_object = json.load(plan_file)
            return plan_object
        except (FileNotFoundError, json.decoder.JSONDecodeError):
            return None

    def __update_status(self, status: ClusterStatusCode):
        logging.debug("Updating status file")
        self.__status = status
        with open(self.__get_cluster_path(STATUS_FILENAME), "w") as status_file:
            status_file.write(status.value)
