from resources.api_view import ApiView
from exceptions.invalid_usage_exception import InvalidUsageException
from models.cloud.openstack_manager import OpenStackManager
from models.user.user import User


class AvailableResourcesApi(ApiView):
    def get(self, user: User, hostname):
        if hostname:
            magic_castle = user.get_magic_castle_by_hostname(hostname)
            return magic_castle.get_available_resources()
        else:
            return OpenStackManager().get_available_resources()
