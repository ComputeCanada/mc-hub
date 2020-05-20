from flask import request
from flask_restful import Resource
from models.invalid_usage import InvalidUsage
from models.magic_castle import MagicCastle


class MagicCastleListResource(Resource):
    def post(self):
        magic_castle = MagicCastle()
        json_data = request.get_json()
        if not json_data:
            return {"message": "No json data was provided"}, 400

        try:
            magic_castle.load_configuration(json_data)
            magic_castle.apply_new()
            return {}
        except InvalidUsage as e:
            return e.get_response()
