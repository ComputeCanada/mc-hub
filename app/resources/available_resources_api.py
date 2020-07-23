from resources.api_view import ApiView
from exceptions.invalid_usage_exception import InvalidUsageException
from models.magic_castle_manager import MagicCastleManager
from models.openstack_manager import OpenStackManager


class AvailableResourcesApi(ApiView):
    def get(self, database_connection, hostname):
        if hostname:
            try:
                magic_castle = MagicCastleManager(database_connection).get_by_hostname(
                    hostname
                )
                return magic_castle.get_available_resources()
            except InvalidUsageException as e:
                return e.get_response()
        else:
            return OpenStackManager().get_available_resources()
