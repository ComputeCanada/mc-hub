from flask import request
from .api_view import ApiView
from ..exceptions.invalid_usage_exception import (
    ClusterNotFoundException,
    InvalidUsageException,
)
from ..models.user import User
from ..models.magic_castle.magic_castle import MagicCastleORM, MagicCastle


class MagicCastleAPI(ApiView):
    def get(self, user: User, hostname):
        if hostname:
            orm = MagicCastleORM.query.filter_by(hostname=hostname).first()
            if orm and orm.project in user.projects:
                return MagicCastle(orm).state
            else:
                raise ClusterNotFoundException
        else:
            return [mc.state for mc in user.magic_castles]

    def post(self, user: User, hostname, apply=False):
        if apply:
            orm = MagicCastleORM.query.filter_by(hostname=hostname).first()
            if orm and orm.project in user.projects:
                magic_castle = MagicCastle(orm)
            else:
                raise ClusterNotFoundException
            magic_castle.apply()
            return {}
        else:
            json_data = request.get_json()
            if not json_data:
                raise InvalidUsageException("No json data was provided")

            magic_castle = MagicCastle()
            magic_castle.plan_creation(json_data)
            return {}

    def put(self, user: User, hostname):
        orm = MagicCastleORM.query.filter_by(hostname=hostname).first()
        if orm and orm.project in user.projects:
            magic_castle = MagicCastle(orm)
        else:
            raise ClusterNotFoundException
        json_data = request.get_json()
        if not json_data:
            raise InvalidUsageException("No json data was provided")
        magic_castle.plan_modification(json_data)
        return {}

    def delete(self, user: User, hostname):
        orm = MagicCastleORM.query.filter_by(hostname=hostname).first()
        if orm and orm.project in user.projects:
            magic_castle = MagicCastle(orm)
        else:
            raise ClusterNotFoundException
        magic_castle.plan_destruction()
        return {}
