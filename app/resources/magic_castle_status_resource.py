from flask_restful import Resource
from models.magic_castle import MagicCastle
from models.cluster_status_code import ClusterStatusCode
from exceptions.cluster_not_found_exception import ClusterNotFoundException


class MagicCastleStatusResource(Resource):
    def get(self, hostname):
        magic_castle = MagicCastle(hostname)
        status = magic_castle.get_status()
        if status in {ClusterStatusCode.NOT_FOUND, ClusterStatusCode.BUILD_SUCCESS}:
            return {
                "status": status.value,
            }
        else:
            progress = magic_castle.get_progress()
            if progress is None:
                return {"status": status.value}
            else:
                return {"status": status.value, "progress": progress}

