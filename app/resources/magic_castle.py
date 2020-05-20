from flask_restful import Resource
from subprocess import run
from threading import Thread
from shutil import rmtree
from utils.cluster_utils import *
from models.invalid_usage import InvalidUsage
import json
from models.terraform_state_parser import TerraformStateParser
from models.magic_castle_schema import MagicCastleSchema


class MagicCastle(Resource):
    def __init__(self):
        self.cluster_name = None

    def launch_cluster_destruction(self):
        if not cluster_exists(self.cluster_name):
            raise InvalidUsage("The cluster does not exist")

        if get_cluster_status(self.cluster_name) != ClusterStatusCode.BUILD_SUCCESS:
            raise InvalidUsage("The cluster is not fully built yet")

        cluster_path = get_cluster_path(self.cluster_name)

        update_cluster_status(self.cluster_name, ClusterStatusCode.DESTROY_RUNNING)

        def destroy_cluster():
            with open(cluster_path + "/terraform_destroy.log", "w") as output_file:
                process = run(
                    [
                        "/usr/bin/env",
                        "terraform",
                        "destroy",
                        "-no-color",
                        "-auto-approve",
                    ],
                    cwd=cluster_path,
                    stdout=output_file,
                    stderr=output_file,
                )

            if process.returncode != 0:
                update_cluster_status(
                    self.cluster_name, ClusterStatusCode.DESTROY_ERROR
                )
            else:
                rmtree(cluster_path)

        destroy_cluster_thread = Thread(target=destroy_cluster)
        destroy_cluster_thread.start()

    def get(self, cluster_name):
        self.cluster_name = cluster_name
        if get_cluster_status(self.cluster_name) != ClusterStatusCode.BUILD_SUCCESS:
            return {"message": "This cluster is not fully built yet"}, 400

        terraform_state_path = path.join(
            get_cluster_path(self.cluster_name), "terraform.tfstate"
        )
        with open(terraform_state_path, "r") as terraform_state_file:
            state = json.load(terraform_state_file)
        parser = TerraformStateParser(state)
        return MagicCastleSchema().dump(parser.get_state_summary())

    def delete(self, cluster_name):
        self.cluster_name = cluster_name
        try:
            self.launch_cluster_destruction()
        except InvalidUsage as e:
            return e.get_response()
        return {}
