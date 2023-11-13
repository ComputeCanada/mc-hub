from ..cloud.openstack_manager import OpenStackManager

MANAGER_CLASSES = {
    "openstack": OpenStackManager,
}

class CloudManager:
    def __init__(self, project, allocated_resources):
        if project:
            manager_class = MANAGER_CLASSES.get(project.provider)
            if manager_class:
                self.manager = manager_class(project, allocated_resources)
            else:
                raise ValueError(f"Unknown cloud provider {project.provider}")
        else:
            self.manager = DefaultCloudManager(project, allocated_resources)

    @property
    def available_resources(self):
        """
        Retrieves the available cloud resources from the cloud provider.
        """
        return self.manager.available_resources

class DefaultCloudManager:
    def __init__(self, project, allocated_resources):
        self.project = project
        self.allocated_resources = allocated_resources

    @property
    def available_resources(self):
        return {
            "quotas": {},
            "possible_resources": {},
            "resource_details": {},
        }
