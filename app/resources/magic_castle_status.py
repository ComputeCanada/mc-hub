from flask_restful import Resource
from utils.cluster_utils import get_cluster_status
from models.cluster_status_code import ClusterStatusCode


class MagicCastleStatus(Resource):
    def get(self, cluster_name):
        status = get_cluster_status(cluster_name)
        if status == ClusterStatusCode.NOT_FOUND:
            return {"message": "The cluster or status file does not exist"}, 404

        return {"status": status.value}
