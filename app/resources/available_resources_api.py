from flask_restful import Api
from resources.api_view import ApiView
from models.magic_castle import MagicCastle
from exceptions.invalid_usage_exception import InvalidUsageException


class AvailableResourcesApi(ApiView):
    def get(self, hostname):
        if hostname:
            try:
                magic_castle = MagicCastle(hostname)
                return magic_castle.get_available_resources()
            except InvalidUsageException as e:
                return e.get_response()
        else:
            magic_castle = MagicCastle()
            return magic_castle.get_available_resources()
