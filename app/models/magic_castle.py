from os import path, environ, getcwd, mkdir
from flask import render_template
from subprocess import run
from shutil import rmtree
from threading import Thread
from marshmallow import ValidationError
from models.cluster_status_code import ClusterStatusCode
from models.magic_castle_schema import MagicCastleSchema
from models.terraform_state_parser import TerraformStateParser
from models.openstack_manager import OpenStackManager
from exceptions.invalid_usage_exception import InvalidUsageException
from exceptions.busy_cluster_exception import BusyClusterException
from exceptions.cluster_not_found_exception import ClusterNotFoundException
from exceptions.cluster_exists_exception import ClusterExistsException
import json

MAGIC_CASTLE_RELEASE_PATH = path.join(
    getcwd(), "magic_castle-openstack-" + environ["MAGIC_CASTLE_VERSION"]
)


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
        status_file_path = self.__get_cluster_path("status.txt")
        if not status_file_path or not path.exists(status_file_path):
            return ClusterStatusCode.NOT_FOUND
        with open(status_file_path, "r") as status_file:
            return ClusterStatusCode(status_file.read())

    def get_state(self):
        if self.__is_busy():
            raise BusyClusterException
        if self.__not_found():
            raise ClusterNotFoundException

        with open(
            self.__get_cluster_path("terraform.tfstate"), "r"
        ) as terraform_state_file:
            state = json.load(terraform_state_file)
        parser = TerraformStateParser(self.__get_cluster_name(), state)
        return MagicCastleSchema().dump(parser.get_state_summary())

    def get_available_resources(self):
        if self.__is_busy():
            raise BusyClusterException

        if self.__found():
            with open(
                self.__get_cluster_path("terraform.tfstate"), "r"
            ) as terraform_state_file:
                state = json.load(terraform_state_file)
            parser = TerraformStateParser(self.__get_cluster_name(), state)

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
        if self.__get_cluster_name():
            return path.join(
                environ["HOME"], "clusters", self.__get_cluster_name(), sub_path
            )
        else:
            return None

    def __get_cluster_name(self):
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
        self.__update_status(ClusterStatusCode.BUILD_RUNNING)

        with open(self.__get_cluster_path("main.tf"), "w") as cluster_config_file:
            cluster_config_file.write(
                render_template(
                    "main.tf",
                    **self.__configuration,
                    magic_castle_release_path=MAGIC_CASTLE_RELEASE_PATH
                )
            )

        def terraform_apply():
            process = run(
                [
                    "terraform",
                    "init",
                    "-no-color",
                    "-plugin-dir",
                    environ["HOME"] + "/.terraform.d/plugin-cache/linux_amd64",
                ],
                cwd=self.__get_cluster_path(),
                capture_output=True,
            )
            if process.returncode == 0:
                with open(
                    self.__get_cluster_path("terraform_apply.log"), "w"
                ) as output_file:
                    process = run(
                        ["terraform", "apply", "-no-color", "-auto-approve"],
                        cwd=self.__get_cluster_path(),
                        stdout=output_file,
                        stderr=output_file,
                    )
            status = (
                ClusterStatusCode.BUILD_SUCCESS
                if process.returncode == 0
                else ClusterStatusCode.BUILD_ERROR
            )
            self.__update_status(status)

        build_cluster_thread = Thread(target=terraform_apply)
        build_cluster_thread.start()

    def destroy(self):
        if self.__is_busy():
            raise BusyClusterException
        if self.__not_found():
            raise ClusterNotFoundException

        self.__update_status(ClusterStatusCode.DESTROY_RUNNING)

        def terraform_destroy():
            with open(
                self.__get_cluster_path("terraform_destroy.log"), "w"
            ) as output_file:
                process = run(
                    [
                        "/usr/bin/env",
                        "terraform",
                        "destroy",
                        "-no-color",
                        "-auto-approve",
                    ],
                    cwd=self.__get_cluster_path(),
                    stdout=output_file,
                    stderr=output_file,
                )

            if process.returncode != 0:
                self.__update_status(ClusterStatusCode.DESTROY_ERROR)
            else:
                rmtree(self.__get_cluster_path())

        destroy_cluster_thread = Thread(target=terraform_destroy)
        destroy_cluster_thread.start()

    def __update_status(self, status: ClusterStatusCode):
        with open(self.__get_cluster_path("status.txt"), "w") as status_file:
            status_file.write(status.value)
