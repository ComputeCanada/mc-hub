from ..cloud.openstack_manager import OpenStackManager
from ..cloud.dns_manager import DnsManager

MANAGER_CLASSES = {
    "openstack": OpenStackManager,
}

class CloudManager:
    def __init__(self, project, **kwargs):
        manager_class = MANAGER_CLASSES.get(project.provider)
        if manager_class:
            self.manager = manager_class(project=project, **kwargs)
        else:
            raise ValueError("Invalid cloud provider")

    @property
    def available_resources(self):
        """
        Retrieves the available cloud resources including resources from OpenStack
        and available domains.
        """
        available_resources = self.manager.available_resources
        available_resources["possible_resources"][
            "domain"
        ] = DnsManager.get_available_domains()
        return available_resources
