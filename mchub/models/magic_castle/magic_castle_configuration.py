import json
import re

from collections.abc import Mapping

import marshmallow
from marshmallow import fields, EXCLUDE

from ..cloud.dns_manager import DnsManager
from ...configuration.magic_castle import (
    MAGIC_CASTLE_SOURCE,
    MAGIC_CASTLE_VERSION,
    MAGIC_CASTLE_PUPPET_CONFIGURATION_URL,
    TERRAFORM_REQUIRED_VERSION,
)

IGNORED_CONFIGURATION_FIELDS = [
    "source",
    "config_git_url",
    "config_version",
    "generate_ssh_key",
    # Legacy fields
    "puppetenv_rev",
]


def validate_cluster_name(cluster_name):
    # Must follow RFC 1035's subdomain naming rules: https://tools.ietf.org/html/rfc1035#section-2.3.1
    return re.search(r"^[a-z]([a-z0-9-]*[a-z0-9]+)?$", cluster_name) is not None


def validate_domain(domain):
    return domain in DnsManager.get_available_domains()


class Schema(marshmallow.Schema):
    """
    Marshmallow schema used to validate, deserialize and serialize Magic Castle configurations.
    This schema is then used in MagicCastleConfiguration to load, create and update a cluster's main.tf.json file.
    """

    cluster_name = fields.Str(required=True, validate=validate_cluster_name)
    domain = fields.Str(required=True, validate=validate_domain)
    image = fields.Str(required=True)
    nb_users = fields.Int(required=True)
    instances = fields.Dict(
        keys=fields.Str(),
        values=fields.Dict(),
        required=True,
    )
    volumes = fields.Dict(
        keys=fields.Str(),
        values=fields.Dict(),
        required=True,
    )
    public_keys = fields.List(fields.Str(), required=True)
    guest_passwd = fields.Str(required=True)
    hieradata = fields.Str(load_default="")


class MagicCastleConfiguration(Mapping):
    """
    MagicCastleConfiguration is responsible for loading and writing Magic Castle configurations.

    Loading can be done using a raw configuration dictionary (__init__),
    or from a main.tf.json file (get_from_main_file)

    All configurations are validated with the configuration schema using the Schema class.
    """

    __slots__ = ["_config", "provider"]

    def __init__(self, provider, configuration):
        """
        Initializes a MagicCastleConfiguration and validates the configuration schema, if present.
        """
        self.provider = provider
        self._config = Schema().load(
            configuration,
            unknown=EXCLUDE,
        )

    def __iter__(self):
        return iter(self._config)

    def __getitem__(self, key):
        return self._config[key]

    def __len__(self):
        return len(self._config)

    @property
    def cluster_name(self):
        return self["cluster_name"]

    @property
    def domain(self):
        return self["domain"]

    @classmethod
    def get_from_main_file(cls, filename):
        """
        Returns a new MagicCastleConfiguration object with the configuration parsed from the main.tf.json file.

        :param filename: path to the main.tf.json file
        :return: The MagicCastleConfiguration object associated with the cluster.
        """
        with open(filename, "r") as main_tf:
            main_tf_data = json.load(main_tf)
        modules = main_tf_data["module"]
        modules.pop("dns", None)
        provider = list(modules.keys())[0]
        configuration = modules[provider]

        for field in IGNORED_CONFIGURATION_FIELDS:
            configuration.pop(field, None)

        return cls(provider, configuration)

    def write(self, filename):
        """
        Formats the configuration and writes it to the cluster's main.tf.json file.
        """

        main_tf_data = {
            "terraform": {"required_version": TERRAFORM_REQUIRED_VERSION},
            "module": {
                self.provider: {
                    "source": MAGIC_CASTLE_SOURCE[self.provider],
                    "generate_ssh_key": True,
                    "config_git_url": MAGIC_CASTLE_PUPPET_CONFIGURATION_URL,
                    "config_version": MAGIC_CASTLE_VERSION,
                    **self,
                }
            },
        }
        main_tf_data["module"].update(
            DnsManager(self["domain"]).get_magic_castle_configuration()
        )

        with open(filename, "w") as main_terraform_file:
            json.dump(main_tf_data, main_terraform_file)
