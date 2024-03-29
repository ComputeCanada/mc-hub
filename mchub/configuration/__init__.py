import json
import logging
import sys

from os import path

from marshmallow import Schema, fields, ValidationError, post_load

from .env import CONFIGURATION_FILE_PATH
from ..models.auth_type import AuthType

CONFIGURATION_FILENAME = "configuration.json"
DATABASE_FILENAME = "database.db"


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


def load_config():
    config_path = path.join(CONFIGURATION_FILE_PATH, CONFIGURATION_FILENAME)
    try:
        with open(config_path) as configuration_file:
            config = json.load(configuration_file)
    except FileNotFoundError as error:
        logging.error(
            f"Could not find {CONFIGURATION_FILENAME} in {CONFIGURATION_FILE_PATH}"
        )
        raise error

    try:
        config = ConfigurationSchema().load(config)
    except ValidationError as error:
        logging.error(
            f"Configuration file {CONFIGURATION_FILENAME} is invalid - {error}"
        )
        raise error
    return config


_config = None


def get_config():
    global _config
    if _config is None:
        _config = load_config()
    return _config
