from flask import request
from resources.api_view import ApiView
from exceptions.invalid_usage_exception import InvalidUsageException
from models.magic_castle.cluster_status_code import ClusterStatusCode
from database.database_manager import DatabaseManager
from models.user.user import User


class MagicCastleAPI(ApiView):
    def get(self, user: User, hostname):
        if hostname:
            magic_castle = user.get_magic_castle_by_hostname(hostname)
            return magic_castle.dump_configuration()
        else:
            return [
                {
                    "cluster_name": magic_castle.get_cluster_name(),
                    "domain": magic_castle.get_domain(),
                    "hostname": magic_castle.get_hostname(),
                    "status": magic_castle.get_status().value,
                }
                for magic_castle in user.get_all_magic_castles()
            ]

    def post(self, user: User, hostname, apply=False):
        if apply:
            magic_castle = user.get_magic_castle_by_hostname(hostname)
            magic_castle.apply()
            return {}
        else:
            magic_castle = user.create_empty_magic_castle()
            json_data = request.get_json()
            if not json_data:
                raise InvalidUsageException("No json data was provided")
            magic_castle.load_configuration(json_data)
            magic_castle.plan_creation()
            return {}

    def put(self, user: User, hostname):
        magic_castle = user.get_magic_castle_by_hostname(hostname)
        json_data = request.get_json()
        if not json_data:
            raise InvalidUsageException("No json data was provided")

        magic_castle.load_configuration(json_data)
        magic_castle.plan_modification()
        return {}

    def delete(self, user: User, hostname):
        magic_castle = user.get_magic_castle_by_hostname(hostname)
        magic_castle.plan_destruction()
        return {}
