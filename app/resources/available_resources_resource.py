from flask_restful import Resource
from models.magic_castle import MagicCastle


class AvailableResourcesResource(Resource):
    def get(self, cluster_name):
        magic_castle = MagicCastle(cluster_name)
        return magic_castle.get_available_resources()
