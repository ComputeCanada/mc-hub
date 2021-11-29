from models.cloud.dns_manager import DnsManager
from models.magic_castle.magic_castle_configuration_schema import (
    MagicCastleConfigurationSchema,
)
from models.constants import (
    MAGIC_CASTLE_MODULE_SOURCE,
    MAGIC_CASTLE_VERSION_TAG,
    MAGIC_CASTLE_PUPPET_CONFIGURATION_URL,
    TERRAFORM_REQUIRED_VERSION,
)
from copy import deepcopy
import json
import marshmallow
from exceptions.server_exception import ServerException

IGNORED_CONFIGURATION_FIELDS = [
    "source",
    "config_git_url",
    "config_version",
    "generate_ssh_key",
    # Legacy fields
    "puppetenv_rev",
]


class MagicCastleConfiguration:
    """
    MagicCastleConfiguration is responsible for loading, updating and dumping Magic Castle configurations.

    Loading can be done using a raw configuration dictionary (get_from_dict),
    or from a main.tf.json file (get_from_main_file)

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
                    configuration,
                    unknown=marshmallow.EXCLUDE,
                )
            except marshmallow.ValidationError as error:
                raise ServerException(
                    f"The cluster configuration is invalid.",
                    additional_details=error.messages,
                )

    @classmethod
    def get_from_dict(cls, configuration_dict):
        """
        Returns a new MagicCastleConfiguration object with the configuration given as a parameter.
        """
        configuration = deepcopy(configuration_dict)

        return cls(configuration)

    @classmethod
    def get_from_main_file(cls, filename):
        """
        Returns a new MagicCastleConfiguration object with the configuration parsed from the main.tf.json file.

        :param filename: path to the main.tf.json file
        :return: The MagicCastleConfiguration object associated with the cluster.
        """
        with open(filename, "r") as main_tf:
            main_tf_configuration = json.load(main_tf)
        configuration = main_tf_configuration["module"]["openstack"]

        for field in IGNORED_CONFIGURATION_FIELDS:
            configuration.pop(field, None)

        return cls(configuration)

    def update_main_file(self, filename):
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
            "hieradata" in main_tf_configuration["module"]["openstack"]
            and len(main_tf_configuration["module"]["openstack"]["hieradata"]) == 0
        ):
            del main_tf_configuration["module"]["openstack"]["hieradata"]

        with open(filename, "w") as main_terraform_file:
            json.dump(main_tf_configuration, main_terraform_file)

    def dump(self):
        """
        Dumps the configuration dictionnary.
        """
        return MagicCastleConfigurationSchema().dump(self.__configuration)

    @property
    def hostname(self):
        return (
            f"{self.__configuration['cluster_name']}.{self.__configuration['domain']}"
        )
