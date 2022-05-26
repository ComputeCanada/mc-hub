from flask import request
from .api_view import ApiView
from ..exceptions.invalid_usage_exception import (
    ClusterNotFoundException,
    InvalidUsageException,
)
from ..models.user import User


class MagicCastleAPI(ApiView):
    def get(self, user: User, hostname):
        if hostname:
            try:
                return user.query_magic_castles(hostname=hostname)[0].state
            except IndexError:
                raise ClusterNotFoundException
        else:
            return [mc.state for mc in user.query_magic_castles()]

    def post(self, user: User, hostname, apply=False):
        if apply:
            try:
                magic_castle = user.query_magic_castles(hostname=hostname)[0]
            except IndexError:
                raise ClusterNotFoundException
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
        try:
            magic_castle = user.query_magic_castles(hostname=hostname)[0]
        except IndexError:
            raise ClusterNotFoundException
        magic_castle.plan_modification(json_data)
        return {}

    def delete(self, user: User, hostname):
        try:
            magic_castle = user.query_magic_castles(hostname=hostname)[0]
        except IndexError:
            raise ClusterNotFoundException
        magic_castle.plan_destruction()
        return {}
