from flask import render_template, request
from flask_restful import Resource
from os import path, mkdir, environ
from marshmallow import Schema, fields, ValidationError, validate
from subprocess import Popen
from threading import Thread

INSTANCE_CATEGORIES = ['mgmt', 'login', 'node']
MAGIC_CASTLE_RELEASE_PATH = '/app/magic_castle-openstack-' + environ['MAGIC_CASTLE_VERSION']
BUILD_CLUSTER_SCRIPT = '/app/build_cluster.sh'


def get_cluster_path(cluster_name):
    return '/app/clusters/' + cluster_name


def validate_cluster_is_unique(cluster_name):
    if path.exists(get_cluster_path(cluster_name)):
        raise ValidationError('The cluster name already exists')


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
        values=fields.Dict(
            type=fields.Str(),
            count=fields.Int()
        ),
        required=True
    )
    storage = fields.Nested(StorageSchema, required=True)
    public_keys = fields.List(fields.Str(), required=True)
    guest_passwd = fields.Str(required=True)
    os_floating_ips = fields.List(fields.Str(), required=True)


magic_castle_schema = MagicCastleSchema()


class MagicCastle(Resource):
    def __init__(self):
        self.magic_castle = None

    def launch_magic_castle_build(self):

        cluster_path = get_cluster_path(self.magic_castle['cluster_name'])
        mkdir(cluster_path)

        magic_castle_config_file = open(cluster_path + '/main.tf', 'w')
        magic_castle_config_file.write(render_template('main.tf', **self.magic_castle,
                                                       magic_castle_release_path=MAGIC_CASTLE_RELEASE_PATH))
        magic_castle_config_file.close()

        status_file_path = cluster_path + '/status.txt'
        with open(status_file_path, 'w') as status_file:
            status_file.write('running')

        def build_magic_castle():
            process = Popen(['/bin/sh', BUILD_CLUSTER_SCRIPT], cwd=cluster_path)
            process.wait()

            with open(status_file_path, 'w') as status_file:
                status_file.write('success' if process.returncode == 0 else 'error')

        build_magic_castle_thread = Thread(target=build_magic_castle)
        build_magic_castle_thread.start()

    def post(self):
        json_data = request.get_json()
        if not json_data:
            return {'message': 'No json data was provided'}, 400

        try:
            self.magic_castle = magic_castle_schema.load(json_data)
            self.launch_magic_castle_build()
            return self.magic_castle
        except ValidationError as e:
            return e.messages, 422
