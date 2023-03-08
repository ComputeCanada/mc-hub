from ..cloud.openstack_manager import OpenStackManager

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
        Retrieves the available cloud resources from the cloud provider.
        """
        return self.manager.available_resources
