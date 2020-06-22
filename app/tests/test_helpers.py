from tests.mocks.openstack.openstack_connection_mock import OpenStackConnectionMock
from pathlib import Path
from os import path
from shutil import rmtree, copytree
import pytest

MOCK_CLUSTERS_PATH = path.join("/tmp", "clusters")


def setup_mock_clusters(cluster_names):
    for cluster_name in cluster_names:
        copytree(
            path.join(Path(__file__).parent, "mock-clusters", cluster_name),
            path.join(MOCK_CLUSTERS_PATH, cluster_name),
        )


def teardown_mock_clusters(cluster_names):
    for cluster_name in cluster_names:
        rmtree(path.join(MOCK_CLUSTERS_PATH, cluster_name))


@pytest.fixture(autouse=True)
def mock_clusters_path(mocker):
    mocker.patch("models.magic_castle.CLUSTERS_PATH", new=MOCK_CLUSTERS_PATH)


@pytest.fixture(autouse=True)
def generate_test_clusters():
    mock_cluster_names = ["empty", "missing-nodes", "valid-1", "missing-floating-ips"]
    setup_mock_clusters(mock_cluster_names)
    yield
    teardown_mock_clusters(mock_cluster_names)


@pytest.fixture(autouse=True)
def mock_openstack_manager(mocker):
    mocker.patch("openstack.connect", return_value=OpenStackConnectionMock())
