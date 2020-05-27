from flask_restful import Resource
from models.magic_castle import MagicCastle
from exceptions.invalid_usage_exception import InvalidUsageException


class AvailableResourcesResource(Resource):
    def get(self, cluster_name):
        try:
            magic_castle = MagicCastle(cluster_name)
            return magic_castle.get_available_resources()
        except InvalidUsageException as e:
            return e.get_response()
