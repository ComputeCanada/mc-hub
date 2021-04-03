from models.configuration import config
from models.constants import MAGIC_CASTLE_MODULE_SOURCE, MAGIC_CASTLE_VERSION_TAG


class DnsManager:
    """
    DnsManager is responsible for creating a DNS configuration that can be used in a Magic Castle configuration
    and providing the list of available domains.

    To do so, DnsManager uses the custom configuration provided in configuration.json.
    """

    def __init__(self, domain):
        self.__domain = domain
        self.__dns_provider = config["domains"][domain].get("dns_provider")

    @staticmethod
    def get_available_domains():
        return list(config["domains"].keys())

    def get_dns_provider(self):
        return self.__dns_provider

    def get_environment_variables(self):
        if self.__dns_provider:
            return config["dns_providers"][self.__dns_provider]["environment_variables"]
        else:
            return {}

    def get_magic_castle_configuration(self):
        if self.__dns_provider:
            magic_castle_configuration = {
                "dns": {
                    "source": f"{MAGIC_CASTLE_MODULE_SOURCE}//dns/{self.__dns_provider}?ref={MAGIC_CASTLE_VERSION_TAG}",
                    "name": "${module.openstack.cluster_name}",
                    "domain": "${module.openstack.domain}",
                    "public_ip": "${module.openstack.ip}",
                    "login_ids": "${module.openstack.login_ids}",
                    "rsa_public_key": "${module.openstack.rsa_public_key}",
                    "ssh_private_key": "${module.openstack.ssh_private_key}",
                    "sudoer_username": "${module.openstack.sudoer_username}",
                }
            }
            magic_castle_configuration["dns"].update(
                config["dns_providers"][self.__dns_provider][
                    "magic_castle_configuration"
                ]
            )
            return magic_castle_configuration
        else:
            return {}
