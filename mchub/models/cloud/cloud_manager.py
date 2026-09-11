from ..cloud.openstack_manager import OpenStackManager
from ..cloud.aws_manager import AWSManager
from ..cloud.dns_manager import DnsManager
from ...services.github_api import get_github_storage
import logging
from time import monotonic

logger = logging.getLogger(__name__)

MANAGER_CLASSES = {
    "aws": AWSManager,
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
        started = monotonic()
        available_resources = self.manager.available_resources
        logger.info("Resource discovery stage=cloud duration=%.3fs", monotonic() - started)
        started = monotonic()
        available_resources["possible_resources"][
            "domain"
        ] = DnsManager.get_available_domains()
        logger.info("Resource discovery stage=domains duration=%.3fs", monotonic() - started)
        started = monotonic()
        available_resources["possible_resources"][
            "mc_version"
        ] = get_github_storage().get_magic_castle_versions()
        logger.info("Resource discovery stage=versions duration=%.3fs", monotonic() - started)
        return available_resources
