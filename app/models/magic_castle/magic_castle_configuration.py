from models.cloud.openstack_manager import OpenStackManager
from models.cloud.dns_manager import DnsManager
from models.magic_castle.magic_castle_configuration_schema import (
    MagicCastleConfigurationSchema,
)
from models.terraform.terraform_state_parser import TerraformStateParser
from models.constants import (
    MAGIC_CASTLE_MODULE_SOURCE,
    MAGIC_CASTLE_VERSION_TAG,
    MAGIC_CASTLE_PUPPET_CONFIGURATION_URL,
    TERRAFORM_STATE_FILENAME,
    CLUSTERS_PATH,
    AUTO_ALLOCATED_IP_LABEL,
    TERRAFORM_REQUIRED_VERSION,
)
from copy import deepcopy
from os import path
import json


MAIN_TERRAFORM_FILENAME = "main.tf.json"

IGNORED_CONFIGURATION_FIELDS = [
    "source",
    "config_git_url",
    "config_version",
    "generate_ssh_key",
    # Legacy fields
    "puppetenv_rev",
]


def get_cluster_path(hostname, sub_path):
    return path.join(CLUSTERS_PATH, hostname, sub_path)


class MagicCastleConfiguration:
    def __init__(self, configuration=None):
        """
        Initializes a MagicCastleConfiguration and validates the configuration schema, if present.
        """
        self.__configuration = None
        if configuration:
            self.__configuration = MagicCastleConfigurationSchema().load(configuration)

    @classmethod
    def get_from_dict(cls, configuration_dict):
        """
        Returns a new MagicCastleConfiguration object with the configuration given as a parameter.
        """
        configuration = deepcopy(configuration_dict)

        # When modifying a cluster, the existing floating ip must be excluded
        # from the configuration, as it does not look available to Open Stack.
        available_floating_ips = set(OpenStackManager().get_available_floating_ips())
        if not set(configuration["os_floating_ips"]).issubset(available_floating_ips):
            configuration["os_floating_ips"] = []

        return cls(configuration)

    @classmethod
    def get_from_main_tf_json_file(
        cls, hostname, *, parse_floating_ips_from_state: bool
    ):
        """
        Returns a new MagicCastleConfiguration object with the configuration parsed from the main.tf.json file.

        :param hostname: the hostname of the cluster.
        :param parse_floating_ips_from_state: If True, it will use the terraform.tfstate file to parse the floating IPs,
        which are not necessarily available in the main.tf.json file.
        :return: The MagicCastleConfiguration object associated with the cluster.
        """
        with open(get_cluster_path(hostname, MAIN_TERRAFORM_FILENAME), "r") as main_tf:
            main_tf_configuration = json.load(main_tf)
        configuration = main_tf_configuration["module"]["openstack"]

        for field in IGNORED_CONFIGURATION_FIELDS:
            configuration.pop(field, None)

        # "node" is the only instance category that is encapsulated in a list
        configuration["instances"]["node"] = configuration["instances"]["node"][0]

        # Try to parse the floating ips from terraform.tfstate
        if parse_floating_ips_from_state:
            with open(
                get_cluster_path(hostname, TERRAFORM_STATE_FILENAME), "r"
            ) as terraform_state_file:
                state = json.load(terraform_state_file)
            parser = TerraformStateParser(state)
            configuration["os_floating_ips"] = parser.get_os_floating_ips()
        else:
            if len(configuration["os_floating_ips"]) == 0:
                # When the floating ips is an empty list, it means it will be automatically allocated
                configuration["os_floating_ips"] = [AUTO_ALLOCATED_IP_LABEL]

        return cls(configuration)

    @classmethod
    def get_from_state_file(cls, hostname):
        """
        Returns a new MagicCastleConfiguration object with the configuration parsed from the terraform.tfstate file.

        Note: the `hieradata` field gets parsed from the main.tf.json file instead, because it is not available in the
        terraform.tfstate file.
        """
        with open(
            get_cluster_path(hostname, TERRAFORM_STATE_FILENAME), "r"
        ) as terraform_state_file:
            state = json.load(terraform_state_file)
        parser = TerraformStateParser(state)
        configuration = parser.get_partial_configuration()

        # Add hieradata to configuration
        with open(get_cluster_path(hostname, MAIN_TERRAFORM_FILENAME), "r") as main_tf:
            main_tf_configuration = json.load(main_tf)

        if main_tf_configuration["module"]["openstack"].get("hieradata"):
            configuration["hieradata"] = main_tf_configuration["module"]["openstack"][
                "hieradata"
            ]
        else:
            configuration["hieradata"] = ""

        return cls(configuration)

    def update_main_tf_json_file(self):
        """
        Formats the configuration and writes it to the cluster's main.tf.json file.
        """

        main_tf_configuration = {
            "terraform": {"required_version": ">= 0.13.4"},
            "module": {
                "openstack": {
                    "source": f"{MAGIC_CASTLE_MODULE_SOURCE}//openstack?ref={MAGIC_CASTLE_VERSION_TAG}",
                    "generate_ssh_key": True,
                    "config_git_url": MAGIC_CASTLE_PUPPET_CONFIGURATION_URL,
                    "config_version": MAGIC_CASTLE_VERSION_TAG,
                    **deepcopy(self.__configuration),
                }
            },
        }
        main_tf_configuration["module"].update(
            DnsManager(self.__configuration["domain"]).get_magic_castle_configuration()
        )

        # "node" is the only instance category that needs to be encapsulated in a list
        main_tf_configuration["module"]["openstack"]["instances"]["node"] = [
            main_tf_configuration["module"]["openstack"]["instances"]["node"]
        ]

        # Magic Castle does not support an empty string in the hieradata field
        if (
            main_tf_configuration["module"]["openstack"].get("hieradata") is not None
            and len(main_tf_configuration["module"]["openstack"]["hieradata"]) == 0
        ):
            del main_tf_configuration["module"]["openstack"]["hieradata"]

        with open(
            get_cluster_path(self.get_hostname(), MAIN_TERRAFORM_FILENAME), "w"
        ) as main_terraform_file:
            json.dump(main_tf_configuration, main_terraform_file)

    def dump(self):
        """
        Dumps the configuration dictionnary.
        """
        return MagicCastleConfigurationSchema().dump(self.__configuration)

    def get_hostname(self):
        return (
            f"{self.__configuration['cluster_name']}.{self.__configuration['domain']}"
        )
