from flask import render_template, request
from flask_restful import Resource
from os import mkdir, environ, path, getcwd
from marshmallow import Schema, fields, ValidationError, validate
from subprocess import run
from threading import Thread
from shutil import rmtree
from utils.cluster_utils import *
from models.invalid_usage import InvalidUsage
import json
from models.terraform_state_parser import TerraformStateParser
from models.constants import INSTANCE_CATEGORIES

MAGIC_CASTLE_RELEASE_PATH = path.join(
    getcwd(), "magic_castle-openstack-" + environ["MAGIC_CASTLE_VERSION"]
)


def validate_cluster_is_unique(cluster_name):
    if cluster_exists(cluster_name):
        raise ValidationError("The cluster name already exists")


class StorageSchema(Schema):
    type = fields.Str(required=True)
    home_size = fields.Int(required=True)
    project_size = fields.Int(required=True)
    scratch_size = fields.Int(required=True)


class MagicCastleSchema(Schema):
    cluster_name = fields.Str(validate=validate_cluster_is_unique, required=True)
    domain = fields.Str(required=True)
    image = fields.Str(required=True)
    nb_users = fields.Int(required=True)
    instances = fields.Dict(
        keys=fields.Str(validate=validate.OneOf(INSTANCE_CATEGORIES)),
        values=fields.Dict(type=fields.Str(), count=fields.Int()),
        required=True,
    )
    storage = fields.Nested(StorageSchema, required=True)
    public_keys = fields.List(fields.Str(), required=True)
    guest_passwd = fields.Str(required=True)
    os_floating_ips = fields.List(fields.Str(), required=True)


magic_castle_schema = MagicCastleSchema()


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
            self.magic_castle = magic_castle_schema.load(json_data)
            self.launch_cluster_build()
            return self.magic_castle
        except ValidationError as e:
            return e.messages, 400


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
        return magic_castle_schema.dump(parser.get_state_summary())

    def delete(self, cluster_name):
        self.cluster_name = cluster_name
        try:
            self.launch_cluster_destruction()
        except InvalidUsage as e:
            return e.get_response()
        return {}
