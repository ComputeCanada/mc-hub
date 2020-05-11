from flask import render_template, request
from flask_restful import Resource
from os import path, mkdir
from marshmallow import Schema, fields, ValidationError, validate

INSTANCE_CATEGORIES = ['mgmt', 'login', 'node']


def get_cluster_path(cluster_name):
    return 'clusters/' + cluster_name


def validate_cluster_is_unique(cluster_name):
    if path.exists(get_cluster_path(cluster_name)):
        raise ValidationError('The cluster name already exists')


def launch_magic_castle_build(magic_castle):
    cluster_path = get_cluster_path(magic_castle['cluster_name'])
    mkdir(cluster_path)
    terraform_config_file = open(cluster_path + '/main.tf', 'w')
    terraform_config_file.write(render_template('main.tf', **magic_castle))
    terraform_config_file.close()


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
    def post(self):
        json_data = request.get_json()
        if not json_data:
            return {'message': 'No json data was provided'}, 400

        try:
            magic_castle = magic_castle_schema.load(json_data)
        except ValidationError as e:
            return e.messages, 422

        launch_magic_castle_build(magic_castle)
        return magic_castle
