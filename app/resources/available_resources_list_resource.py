from flask_restful import Resource
from models.magic_castle import MagicCastle


class AvailableResourcesListResource(Resource):
    def get(self):
        magic_castle = MagicCastle()
        return magic_castle.get_available_resources()
