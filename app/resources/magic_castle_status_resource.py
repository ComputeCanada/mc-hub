from flask_restful import Resource
from models.magic_castle import MagicCastle


class MagicCastleStatusResource(Resource):
    def get(self, cluster_name):
        magic_castle = MagicCastle(cluster_name)
        return {"status": magic_castle.get_status().value}
