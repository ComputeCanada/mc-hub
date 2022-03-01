import json
import logging
import sys

from os import path

from marshmallow import Schema, fields, ValidationError

from models.constants import CONFIGURATION_FILE_PATH, CONFIGURATION_FILENAME

class Configuration(Schema):
    auth_type = fields.Str(required=True)
    admins = fields.List(fields.Str())
    admin_ips = fields.List(fields.Str())
    cors_allowed_origins = fields.List(fields.Str(), required=True)
    domains = fields.Dict()
    dns_providers = fields.Dict()
    port = fields.Integer(load_default=5000)
    debug = fields.Boolean(load_default=True)

config_path = path.join(CONFIGURATION_FILE_PATH, CONFIGURATION_FILENAME)
try:
    with open(config_path) as configuration_file:
        config = json.load(configuration_file)
except FileNotFoundError:
    logging.error(f"Could not find {CONFIGURATION_FILENAME} in {CONFIGURATION_FILE_PATH}")
    sys.exit(1)

try:
    config = Configuration().load(config)
except ValidationError as error:
    logging.error(f"Configuration file {CONFIGURATION_FILENAME} is invalid - {error}")
    sys.exit(1)
