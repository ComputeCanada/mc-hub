from flask_restful import Resource
from models.magic_castle import MagicCastle
from models.cluster_status_code import ClusterStatusCode
from exceptions.cluster_not_found_exception import ClusterNotFoundException
from exceptions.invalid_usage_exception import InvalidUsageException


class MagicCastleApplyResource(Resource):
    def post(self, hostname):
        magic_castle = MagicCastle(hostname)
        try:
            magic_castle.apply()
            return {}
        except InvalidUsageException as e:
            return e.get_response()
