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
import marshmallow
from exceptions.server_exception import ServerException


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
    """
    MagicCastleConfiguration is responsible for loading, updating and dumping Magic Castle configurations.

    Loading can be done using a raw configuration dictionary (get_from_dict),
    from a main.tf.json file (get_from_main_tf_json_file), or from a Terraform state file (get_from_state_file).

    All configurations are validated with the configuration schema using the MagicCastleSchema class.
    """

    def __init__(self, configuration=None):
        """
        Initializes a MagicCastleConfiguration and validates the configuration schema, if present.
        """
        self.__configuration = None
        if configuration:
            try:
                self.__configuration = MagicCastleConfigurationSchema().load(
                    configuration
                )
            except marshmallow.ValidationError:
                raise ServerException("The cluster configuration is invalid.")

    @classmethod
    def get_from_dict(cls, configuration_dict):
        """
        Returns a new MagicCastleConfiguration object with the configuration given as a parameter.
        """
        configuration = deepcopy(configuration_dict)

        return cls(configuration)

    @classmethod
    def get_from_main_tf_json_file(cls, hostname):
        """
        Returns a new MagicCastleConfiguration object with the configuration parsed from the main.tf.json file.

        :param hostname: the hostname of the cluster.
        :return: The MagicCastleConfiguration object associated with the cluster.
        """
        with open(get_cluster_path(hostname, MAIN_TERRAFORM_FILENAME), "r") as main_tf:
            main_tf_configuration = json.load(main_tf)
        configuration = main_tf_configuration["module"]["openstack"]

        for field in IGNORED_CONFIGURATION_FIELDS:
            configuration.pop(field, None)

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

        # Add cluster_name and domain. When the terraform state file is empty,
        # these variables must still be parsed correctly to create a valid MagicCastleConfiguration object.
        [cluster_name, domain] = hostname.split(".", 1)
        configuration["cluster_name"] = cluster_name
        configuration["domain"] = domain

        # Add missing parameter to configuration
        with open(get_cluster_path(hostname, MAIN_TERRAFORM_FILENAME), "r") as main_tf:
            main_tf_configuration = json.load(main_tf)

        configuration["nb_users"] = main_tf_configuration["module"]["openstack"].get("nb_users", 0)
        configuration["hieradata"] = main_tf_configuration["module"]["openstack"].get("hieradata", "")
        configuration["guest_passwd"] = main_tf_configuration["module"]["openstack"].get("guest_passwd", "")
        configuration["volumes"] = main_tf_configuration["module"]["openstack"].get("volumes", {})
        configuration["public_keys"] = main_tf_configuration["module"]["openstack"].get("public_keys", [])
        
        for key, value in configuration["instances"].items():
            instance = main_tf_configuration["module"]["openstack"]["instances"].get(key, {})
            value["tags"] = instance.get("tags", [])

        return cls(configuration)

    def update_main_tf_json_file(self):
        """
        Formats the configuration and writes it to the cluster's main.tf.json file.
        """

        main_tf_configuration = {
            "terraform": {"required_version": TERRAFORM_REQUIRED_VERSION},
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
