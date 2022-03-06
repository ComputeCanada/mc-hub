import json
import logging
import sys

from os import path

from marshmallow import Schema, fields, ValidationError, post_load

from . constants import CONFIGURATION_FILE_PATH, CONFIGURATION_FILENAME
from . models.auth_type import AuthType


class ConfigurationSchema(Schema):
    auth_type = fields.List(fields.Str(required=True))
    admins = fields.List(fields.Str())
    token = fields.Str()
    cors_allowed_origins = fields.List(fields.Str(), required=True)
    domains = fields.Dict()
    dns_providers = fields.Dict()
    port = fields.Integer(load_default=5000)
    debug = fields.Boolean(load_default=True)

# validation
#         if AuthType.TOKEN in data["auth_type"] and data.get("token", "") == "":
#             raise Exception("Authorization token is missing")

    @post_load
    def make_auth_type(self, data, **kwargs):
        data["auth_type"] = [AuthType(auth) for auth in data["auth_type"]]
        return data

config_path = path.join(CONFIGURATION_FILE_PATH, CONFIGURATION_FILENAME)
try:
    with open(config_path) as configuration_file:
        config = json.load(configuration_file)
except FileNotFoundError:
    logging.error(f"Could not find {CONFIGURATION_FILENAME} in {CONFIGURATION_FILE_PATH}")
    sys.exit(1)

try:
    config = ConfigurationSchema().load(config)
except ValidationError as error:
    logging.error(f"Configuration file {CONFIGURATION_FILENAME} is invalid - {error}")
    sys.exit(1)
