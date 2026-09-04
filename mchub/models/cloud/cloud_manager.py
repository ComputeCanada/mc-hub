from ..cloud.openstack_manager import OpenStackManager
from ..cloud.dns_manager import DnsManager
from ...services.github_api import get_github_storage

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
        available_resources["possible_resources"][
            "version"
        ] = get_github_storage().get_magic_castle_versions()
        return available_resources
