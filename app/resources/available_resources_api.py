from resources.api_view import ApiView
from exceptions.invalid_usage_exception import InvalidUsageException
from models.cloud.cloud_manager import CloudManager
from models.user.user import User


class AvailableResourcesApi(ApiView):
    def get(self, user: User, hostname):
        if hostname:
            magic_castle = user.get_magic_castle_by_hostname(hostname)
            return magic_castle.get_available_resources()
        else:
            return CloudManager().get_available_resources()
