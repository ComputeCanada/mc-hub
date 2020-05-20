from flask_restful import Resource
from flask import request
from models.invalid_usage import InvalidUsage
from models.magic_castle import MagicCastle


class MagicCastleResource(Resource):
    def __init__(self):
        self.cluster_name = None

    def get(self, cluster_name):
        magic_castle = MagicCastle(cluster_name)
        try:
            return magic_castle.get_state()
        except InvalidUsage as e:
            return e.get_response()

    def put(self, cluster_name):
        magic_castle = MagicCastle(cluster_name)
        json_data = request.get_json()

        if not json_data:
            return {"message": "No json data was provided"}, 400

        try:
            magic_castle.load_configuration(json_data)
            magic_castle.apply_existing()
            return {}
        except InvalidUsage as e:
            return e.get_response()

    def delete(self, cluster_name):
        magic_castle = MagicCastle(cluster_name)
        try:
            magic_castle.destroy()
            return {}
        except InvalidUsage as e:
            return e.get_response()
