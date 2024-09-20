from ... configuration import config
from ... configuration.magic_castle import MAGIC_CASTLE_SOURCE


class DnsManager:
    """
    DnsManager is responsible for creating a DNS configuration that can be used in a Magic Castle configuration
    and providing the list of available domains.

    To do so, DnsManager uses the custom configuration provided in configuration.json.
    """

    def __init__(self, domain):
        self.domain = domain
        self.provider = config["domains"][domain].get("dns_provider")
        self.module = config["dns_providers"][self.provider]["module"]

    @staticmethod
    def get_available_domains():
        return list(config["domains"].keys())

    def get_dns_provider(self):
        return self.provider

    def get_environment_variables(self):
        if self.provider:
            return config["dns_providers"][self.provider]["environment_variables"]
        else:
            return {}

    def get_magic_castle_configuration(self):
        if self.provider:
            magic_castle_configuration = {
                "dns": {
                    "source": MAGIC_CASTLE_SOURCE['dns'][self.module],
                    "name": "${module.openstack.cluster_name}",
                    "domain": "${module.openstack.domain}",
                    "public_instances": "${module.openstack.public_instances}",
                }
            }
            magic_castle_configuration["dns"].update(
                config["dns_providers"][self.provider][
                    "magic_castle_configuration"
                ]
            )

            return magic_castle_configuration
        else:
            return {}
