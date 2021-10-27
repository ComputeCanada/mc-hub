from resources.api_view import ApiView
from models.cloud.cloud_manager import CloudManager
from models.user.user import User


class AvailableResourcesApi(ApiView):
    def get(self, user: User, hostname):
        if hostname:
            source = user.get_magic_castle_by_hostname(hostname)
        else:
            source = CloudManager()
        return source.get_available_resources()
