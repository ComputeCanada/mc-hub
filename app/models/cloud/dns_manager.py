from models.configuration import configuration


class DnsManager:
    def __init__(self, domain):
        self.__domain = domain
        self.__dns_provider = configuration["domains"][domain].get("dns_provider")

    @staticmethod
    def get_available_domains():
        return list(configuration["domains"].keys())

    def get_dns_provider(self):
        return self.__dns_provider

    def get_environment_variables(self):
        if self.__dns_provider:
            return configuration["dns_providers"][self.__dns_provider][
                "environment_variables"
            ]
        else:
            return {}

    def get_magic_castle_configuration(self):
        if self.__dns_provider:
            dns_configuration = {
                "dns": {
                    "source": f"git::https://github.com/ComputeCanada/magic_castle.git//dns/{self.__dns_provider}",
                    "name": "${module.openstack.cluster_name}",
                    "domain": "${module.openstack.domain}",
                    "public_ip": "${module.openstack.ip}",
                    "login_ids": "${module.openstack.login_ids}",
                    "rsa_public_key": "${module.openstack.rsa_public_key}",
                    "ssh_private_key": "${module.openstack.ssh_private_key}",
                    "sudoer_username": "${module.openstack.sudoer_username}",
                }
            }
            dns_configuration["dns"].update(
                configuration["dns_providers"][self.__dns_provider][
                    "magic_castle_configuration"
                ]
            )
            return dns_configuration
        else:
            return {}
