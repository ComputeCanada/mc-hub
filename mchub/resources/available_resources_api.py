from .. configuration.cloud import DEFAULT_CLOUD
from .. resources.api_view import ApiView
from .. models.cloud.cloud_manager import CloudManager
from .. models.user.user import User


class AvailableResourcesApi(ApiView):
    def get(self, user: User, hostname, cloud_id):
        allocated_resources = {}
        if hostname:
            mc = user.get_magic_castle_by_hostname(hostname)
            cloud_id = mc.cloud_id
            allocated_resources = mc.allocated_resources
        cloud = CloudManager(cloud_id=cloud_id, **allocated_resources)
        return cloud.available_resources
