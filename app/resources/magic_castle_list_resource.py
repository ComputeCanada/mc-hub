from flask import request
from flask_restful import Resource
from exceptions.invalid_usage_exception import InvalidUsageException
from models.magic_castle import MagicCastle


class MagicCastleListResource(Resource):
    def get(self):
        return [
            {
                "name": magic_castle.get_name(),
                "status": magic_castle.get_status().value,
            }
            for magic_castle in MagicCastle.all()
        ]

    def post(self):
        magic_castle = MagicCastle()
        json_data = request.get_json()
        if not json_data:
            return {"message": "No json data was provided"}, 400

        try:
            magic_castle.load_configuration(json_data)
            magic_castle.apply_new()
            return {}
        except InvalidUsageException as e:
            return e.get_response()
