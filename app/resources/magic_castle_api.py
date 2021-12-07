from flask import request
from resources.api_view import ApiView
from exceptions.invalid_usage_exception import InvalidUsageException
from models.user.user import User


class MagicCastleAPI(ApiView):
    def get(self, user: User, hostname):
        if hostname:
            return user.get_magic_castle_by_hostname(hostname).dump_state()
        else:
            return [mc.dump_state() for mc in user.get_all_magic_castles()]

    def post(self, user: User, hostname, apply=False):
        if apply:
            magic_castle = user.get_magic_castle_by_hostname(hostname)
            magic_castle.apply()
            return {}
        else:
            json_data = request.get_json()
            if not json_data:
                raise InvalidUsageException("No json data was provided")
            magic_castle = user.create_empty_magic_castle()
            magic_castle.plan_creation(json_data)
            return {}

    def put(self, user: User, hostname):
        json_data = request.get_json()
        if not json_data:
            raise InvalidUsageException("No json data was provided")
        magic_castle = user.get_magic_castle_by_hostname(hostname)
        magic_castle.plan_modification(json_data)
        return {}

    def delete(self, user: User, hostname):
        magic_castle = user.get_magic_castle_by_hostname(hostname)
        magic_castle.plan_destruction()
        return {}
