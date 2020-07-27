from marshmallow import Schema, fields, validate
from models.constants import INSTANCE_CATEGORIES
import re


class StorageSchema(Schema):
    type = fields.Str(required=True)
    home_size = fields.Int(required=True)
    project_size = fields.Int(required=True)
    scratch_size = fields.Int(required=True)


def validate_cluster_name(cluster_name):
    return re.search(r"^[a-z][a-z0-9]*$", cluster_name) is not None


class MagicCastleConfigurationSchema(Schema):
    cluster_name = fields.Str(required=True, validate=validate_cluster_name)
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
