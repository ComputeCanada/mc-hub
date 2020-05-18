from models.cluster_status_code import ClusterStatusCode
from os import path


def get_cluster_path(cluster_name):
    return '/clusters/' + cluster_name


def cluster_exists(cluster_name):
    return path.exists(get_cluster_path(cluster_name))


def update_cluster_status(cluster_name: str, status: ClusterStatusCode):
    status_file_path = get_cluster_path(cluster_name) + '/status.txt'
    with open(status_file_path, 'w') as status_file:
        status_file.write(status.value)


def get_cluster_status(cluster_name: str) -> ClusterStatusCode:
    status_file_path = get_cluster_path(cluster_name) + '/status.txt'
    if not path.exists(status_file_path):
        return ClusterStatusCode.NOT_FOUND
    with open(status_file_path, 'r') as status_file:
        return ClusterStatusCode(status_file.read())
