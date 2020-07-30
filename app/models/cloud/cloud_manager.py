from models.cloud.openstack_manager import OpenStackManager
from models.cloud.dns_manager import DnsManager


class CloudManager:
    def __init__(self, **kwargs):
        self.__openstack_manager = OpenStackManager(**kwargs)

    def get_available_resources(self):
        """
        Retrieves the available cloud resources including resources from OpenStack
        and availables domains.
        """
        available_resources = self.__openstack_manager.get_available_resources()
        available_resources["possible_resources"][
            "domain"
        ] = DnsManager.get_available_domains()
        return available_resources
