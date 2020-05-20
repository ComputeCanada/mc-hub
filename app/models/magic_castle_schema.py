from marshmallow import Schema, fields, ValidationError, validate
from utils.cluster_utils import *
from models.constants import INSTANCE_CATEGORIES


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
