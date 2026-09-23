import json
import logging
import sys

from os import path
from typing import Optional

from marshmallow import Schema, fields, ValidationError, post_load, validates_schema
from marshmallow.validate import OneOf, Regexp, URL, Length

from .env import CONFIGURATION_FILE_PATH
from ..models.auth_type import AuthType
from ..models.version_constraint import parse_terraform_version_constraint

CONFIGURATION_FILENAME = "configuration.json"
DATABASE_FILENAME = "database.db"


def validate_magic_castle_version_range(value):
    try:
        parse_terraform_version_constraint(value)
    except ValueError as error:
        raise ValidationError(str(error)) from error


class OpenStackCloudSchema(Schema):
    agent_pool_name = fields.Str(load_default=None, allow_none=True, validate=Length(min=1))
    name = fields.Str(required=True, validate=Length(min=1))
    auth_url = fields.Str(required=True, validate=URL(schemes={"https", "http"}))


class ServiceStatusProviderSchema(Schema):
    id = fields.Str(required=True, validate=Regexp(r"^[a-z][a-z0-9_]{0,99}$"))
    name = fields.Str(required=True, validate=Length(min=1))
    adapter = fields.Str(required=True, validate=OneOf(["statuspage", "hashicorp_rss"]))
    enabled = fields.Bool(load_default=True)
    feed_url = fields.Str(required=True, validate=URL(schemes={"https"}))
    status_url = fields.Str(required=True, validate=URL(schemes={"https"}))
    components = fields.List(fields.Str(validate=Length(min=1)), required=True, validate=Length(min=1))


class NotificationDestinationSchema(Schema):
    id = fields.Str(required=True, validate=Regexp(r"^[a-z][a-z0-9_]{0,99}$"))
    type = fields.Str(required=True, validate=OneOf(["slack", "webhook"]))
    url = fields.Str(required=True, validate=URL(schemes={"https"}))
    enabled = fields.Bool(load_default=True)
    token = fields.Str(validate=Regexp(r"^[^\r\n]+$"))


class ConfigurationSchema(Schema):
    notification_destinations = fields.List(fields.Nested(NotificationDestinationSchema), load_default=list)

    @validates_schema
    def unique_notification_destinations(self, data, **kwargs):
        ids = [d["id"] for d in data.get("notification_destinations", [])]
        if len(ids) != len(set(ids)):
            raise ValidationError("Notification destination IDs must be unique")

    service_status_providers = fields.List(fields.Nested(ServiceStatusProviderSchema))

    @validates_schema
    def unique_status_providers(self, data, **kwargs):
        ids = [p["id"] for p in data.get("service_status_providers", [])]
        if len(ids) != len(set(ids)):
            raise ValidationError("Service status provider IDs must be unique")

    auth_type = fields.List(fields.Str(required=True))
    admins = fields.List(fields.Str())
    token = fields.Str()
    cors_allowed_origins = fields.List(fields.Str(), required=True)
    openstack_clouds = fields.List(fields.Nested(OpenStackCloudSchema), load_default=list)
    domains = fields.Dict()
    dns_providers = fields.Dict()
    port = fields.Integer(load_default=5000)
    debug = fields.Boolean(load_default=True)
    github_token = fields.Str()
    github_organization = fields.Str()
    github_templates = fields.Dict(
        keys=fields.Str(validate=OneOf(["aws", "openstack", "azure", "gcp", "ovh"])),
        values=fields.Str(validate=Regexp(
            r"^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/?$",
            error="Use a GitHub repository URL: https://github.com/owner/repository",
        )),
        load_default=dict,
    )
    magic_castle_version_range = fields.Str(
        required=True,
        validate=validate_magic_castle_version_range,
    )
    additional_mig_profiles = fields.List(
        fields.Str(validate=Regexp(
            r"^[1-7]g\.\S+$",
            error="Use a profile starting with 1g. through 7g., followed by a name without spaces.",
        )),
        load_default=list,
    )
    tfcloud_api_token = fields.Str()
    tfcloud_organization = fields.Str()
    tfcloud_autoscale_pool_variable = fields.Str(load_default="pool", validate=Regexp(r"^[A-Za-z_][A-Za-z0-9_-]*$"))
    tfcloud_oauth_vcs_token_id = fields.Str()
    mchub_url = fields.Str(load_default=None)

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
            config_json = json.load(configuration_file)
    except FileNotFoundError as error:
        logging.error(
            f"Could not find {CONFIGURATION_FILENAME} in {CONFIGURATION_FILE_PATH}"
        )
        raise error

    try:
        config = ConfigurationSchema().load(config_json)
    except ValidationError as error:
        logging.error(
            f"Configuration file {CONFIGURATION_FILENAME} is invalid - {error}"
        )
        raise error
    return config


_config = None


def get_config() -> ConfigurationSchema:
    global _config
    if _config is None:
        _config = load_config()
    return _config
