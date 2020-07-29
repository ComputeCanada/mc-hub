from models.openstack_manager import OpenStackManager
from models.magic_castle.magic_castle_configuration_schema import (
    MagicCastleConfigurationSchema,
)
from models.terraform.terraform_state_parser import TerraformStateParser
from models.constants import (
    MAGIC_CASTLE_RELEASE_PATH,
    TERRAFORM_STATE_FILENAME,
    CLUSTERS_PATH,
    AUTO_ALLOCATED_IP_LABEL,
)
from copy import deepcopy
from os import path
import json


MAIN_TERRAFORM_FILENAME = "main.tf.json"


def get_cluster_path(hostname, sub_path):
    return path.join(CLUSTERS_PATH, hostname, sub_path)


class MagicCastleConfiguration:
    def __init__(self, configuration=None):
        """
        Initializes a MagicCastleConfiguration and validates the configuration schema, if present.
        """
        self.__configuration = {}
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
    def get_from_state_file(cls, hostname):
        """
        Returns a new MagicCastleConfiguration object with the configuration parsed from the terraform.tfstate file.
        """
        with open(
            get_cluster_path(hostname, TERRAFORM_STATE_FILENAME), "r"
        ) as terraform_state_file:
            state = json.load(terraform_state_file)
        parser = TerraformStateParser(state)
        return cls(parser.get_configuration())

    @classmethod
    def get_from_main_tf_json_file(cls, hostname):
        """
        Returns a new MagicCastleConfiguration object with the configuration parsed from the main.tf.json file.
        """
        with open(get_cluster_path(hostname, MAIN_TERRAFORM_FILENAME), "r") as main_tf:
            main_tf_configuration = json.load(main_tf)
        configuration = main_tf_configuration["module"]["openstack"]
        del configuration["source"]

        # "node" is the only instance category that is encapsulated in a list
        configuration["instances"]["node"] = configuration["instances"]["node"][0]

        if len(configuration["os_floating_ips"]) == 0:
            # When the floating ips is an empty list, it means it will be automatically allocated
            configuration["os_floating_ips"] = [AUTO_ALLOCATED_IP_LABEL]

        return cls(configuration)

    def update_main_tf_json_file(self):
        """
        Formats the configuration and writes it to the cluster's main.tf.json file.
        """

        openstack_module_source = path.join(MAGIC_CASTLE_RELEASE_PATH, "openstack")
        main_tf_configuration = {
            "terraform": {"required_version": ">= 0.12.21"},
            "module": {
                "openstack": {
                    "source": openstack_module_source,
                    **deepcopy(self.__configuration),
                }
            },
        }

        # "node" is the only instance category that needs to be encapsulated in a list
        main_tf_configuration["module"]["openstack"]["instances"]["node"] = [
            main_tf_configuration["module"]["openstack"]["instances"]["node"]
        ]
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
