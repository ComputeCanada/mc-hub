import re

from marshmallow import Schema, fields, validate

from .. cloud.dns_manager import DnsManager
from ... constants import INSTANCE_CATEGORIES

def validate_cluster_name(cluster_name):
    # Must follow RFC 1035's subdomain naming rules: https://tools.ietf.org/html/rfc1035#section-2.3.1
    return re.search(r"^[a-z]([a-z0-9-]*[a-z0-9]+)?$", cluster_name) is not None


def validate_domain(domain):
    return domain in DnsManager.get_available_domains()


class MagicCastleConfigurationSchema(Schema):
    """
    Marshmallow schema used to validate, deserialize and serialize Magic Castle configurations.
    This schema is then used in MagicCastleConfiguration to load, create and update a cluster's main.tf.json file.
    """
    cluster_name = fields.Str(required=True, validate=validate_cluster_name)
    domain = fields.Str(required=True, validate=validate_domain)
    image = fields.Str(required=True)
    nb_users = fields.Int(required=True)
    instances = fields.Dict(
        keys=fields.Str(validate=validate.OneOf(INSTANCE_CATEGORIES)),
        values=fields.Dict(type=fields.Str(), count=fields.Int(), tags=fields.List(fields.Str())),
        required=True,
    )
    volumes = fields.Dict(
        keys=fields.Str(),
        values=fields.Dict(
            type=fields.Str(), 
            size=fields.Int(),
        ),
        required=True
    )
    public_keys = fields.List(fields.Str(), required=True)
    guest_passwd = fields.Str(required=True)
    hieradata = fields.Str(missing="")

