from flask_restful import Resource
from flask import request
from exceptions.invalid_usage_exception import InvalidUsageException
from models.magic_castle import MagicCastle


class MagicCastleResource(Resource):
    def get(self, hostname):
        magic_castle = MagicCastle(hostname)
        try:
            return magic_castle.get_state()
        except InvalidUsageException as e:
            return e.get_response()

    def put(self, hostname):
        magic_castle = MagicCastle(hostname)
        json_data = request.get_json()

        if not json_data:
            return {"message": "No json data was provided"}, 400

        try:
            magic_castle.load_configuration(json_data)
            magic_castle.plan_modification()
            return {}
        except InvalidUsageException as e:
            return e.get_response()

    def delete(self, hostname):
        magic_castle = MagicCastle(hostname)
        try:
            magic_castle.plan_destruction()
            return {}
        except InvalidUsageException as e:
            return e.get_response()
