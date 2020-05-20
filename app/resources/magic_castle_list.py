from flask import render_template, request
from flask_restful import Resource
from os import mkdir, getcwd
from marshmallow import ValidationError
from subprocess import run
from threading import Thread
from utils.cluster_utils import *
from models.invalid_usage import InvalidUsage
from models.magic_castle_schema import MagicCastleSchema

MAGIC_CASTLE_RELEASE_PATH = path.join(
    getcwd(), "magic_castle-openstack-" + environ["MAGIC_CASTLE_VERSION"]
)


class MagicCastleList(Resource):
    def __init__(self):
        self.magic_castle = None
        self.cluster_name = None

    def launch_cluster_build(self):
        self.cluster_name = self.magic_castle["cluster_name"]
        cluster_path = get_cluster_path(self.cluster_name)
        mkdir(cluster_path)

        cluster_config_file = open(cluster_path + "/main.tf", "w")
        cluster_config_file.write(
            render_template(
                "main.tf",
                **self.magic_castle,
                magic_castle_release_path=MAGIC_CASTLE_RELEASE_PATH
            )
        )
        cluster_config_file.close()

        update_cluster_status(self.cluster_name, ClusterStatusCode.BUILD_RUNNING)

        def build_cluster():
            process = run(
                [
                    "terraform",
                    "init",
                    "-no-color",
                    "-plugin-dir",
                    environ["HOME"] + "/.terraform.d/plugin-cache/linux_amd64",
                ],
                cwd=cluster_path,
                capture_output=True,
            )
            if process.returncode == 0:
                with open(cluster_path + "/terraform_apply.log", "w") as output_file:
                    process = run(
                        ["terraform", "apply", "-no-color", "-auto-approve",],
                        cwd=cluster_path,
                        stdout=output_file,
                        stderr=output_file,
                    )
            status = (
                ClusterStatusCode.BUILD_SUCCESS
                if process.returncode == 0
                else ClusterStatusCode.BUILD_ERROR
            )
            update_cluster_status(self.cluster_name, status)

        build_cluster_thread = Thread(target=build_cluster)
        build_cluster_thread.start()

    def post(self):
        json_data = request.get_json()
        if not json_data:
            raise InvalidUsage("No json data was provided", 400)

        try:
            self.magic_castle = MagicCastleSchema().load(json_data)
            self.launch_cluster_build()
            return self.magic_castle
        except ValidationError as e:
            return e.messages, 400
