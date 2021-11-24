from resources.api_view import ApiView
from models.cloud.cloud_manager import CloudManager
from models.user.user import User


class AvailableResourcesApi(ApiView):
    def get(self, user: User, hostname):
        allocated_resources = {}
        if hostname:
            allocated_resources = user.get_magic_castle_by_hostname(
                hostname
            ).get_allocated_resources()
        cloud = CloudManager(**allocated_resources)
        return cloud.get_available_resources()
