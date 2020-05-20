from os import path, environ, getcwd, mkdir
from flask import render_template
from models.cluster_status_code import ClusterStatusCode
from subprocess import run
from shutil import rmtree
from threading import Thread
from models.magic_castle_schema import MagicCastleSchema
from marshmallow import ValidationError
from models.invalid_usage import InvalidUsage
from models.terraform_state_parser import TerraformStateParser
import json

MAGIC_CASTLE_RELEASE_PATH = path.join(
    getcwd(), "magic_castle-openstack-" + environ["MAGIC_CASTLE_VERSION"]
)


class MagicCastle:
    """
    Magic Castle is the class that manage the state of Magic Castle clusters.
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
            raise InvalidUsage("The magic castle configuration could not be parsed")

    def get_status(self) -> ClusterStatusCode:
        status_file_path = self.__get_cluster_path("status.txt")
        if not status_file_path or not path.exists(status_file_path):
            return ClusterStatusCode.NOT_FOUND
        with open(status_file_path, "r") as status_file:
            return ClusterStatusCode(status_file.read())

    def get_state(self):
        if self.get_status() != ClusterStatusCode.BUILD_SUCCESS:
            raise InvalidUsage("This cluster is not fully built yet")

        with open(
            self.__get_cluster_path("terraform.tfstate"), "r"
        ) as terraform_state_file:
            state = json.load(terraform_state_file)
        parser = TerraformStateParser(state)
        return MagicCastleSchema().dump(parser.get_state_summary())

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
        if self.get_status() != ClusterStatusCode.NOT_FOUND:
            raise InvalidUsage("The cluster already exists")
        mkdir(self.__get_cluster_path())
        return self.__apply()

    def apply_existing(self):
        if self.get_status() == ClusterStatusCode.NOT_FOUND:
            raise InvalidUsage("The cluster does not exist")
        elif self.get_status() in [
            ClusterStatusCode.BUILD_RUNNING,
            ClusterStatusCode.DESTROY_RUNNING,
        ]:
            raise InvalidUsage("The cluster is not ready")
        return self.__apply()

    def __apply(self):
        self.__update_status(ClusterStatusCode.BUILD_RUNNING)

        # New cluster
        if not path.exists(self.__get_cluster_path()):
            mkdir(self.__get_cluster_path())

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
                        ["terraform", "apply", "-no-color", "-auto-approve",],
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
        if self.get_status() != ClusterStatusCode.BUILD_SUCCESS:
            raise InvalidUsage("The cluster is not fully built yet")

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
