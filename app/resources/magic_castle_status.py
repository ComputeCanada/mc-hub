from flask_restful import Resource
from resources.magic_castle import get_cluster_path
from os import path


class MagicCastleStatus(Resource):
    def get(self, cluster_name):
        cluster_path = get_cluster_path(cluster_name)
        if not path.exists(cluster_path):
            return {'message': 'The cluster does not exist'}, 404

        status_file_path = get_cluster_path(cluster_name) + '/status.txt'
        if not path.exists(status_file_path):
            return {'message': 'The status file for this cluster does not exist'}, 500

        status = open(status_file_path, 'r').read()
        return {'status': status}
