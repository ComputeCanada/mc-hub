from tests.mocks.openstack.openstack_connection_mock import OpenStackConnectionMock
from pathlib import Path
from os import path
from shutil import rmtree, copytree
import pytest


def setup_mock_clusters(cluster_names):
    for cluster_name in cluster_names:
        copytree(
            path.join(Path(__file__).parent, "mock-clusters", cluster_name),
            f"/home/mcu/clusters/{cluster_name}",
        )


def teardown_mock_clusters(cluster_names):
    for cluster_name in cluster_names:
        rmtree(f"/home/mcu/clusters/{cluster_name}")


@pytest.fixture(autouse=True)
def generate_test_clusters():
    mock_cluster_names = ["empty", "missing-nodes", "valid-1"]
    setup_mock_clusters(mock_cluster_names)
    yield
    teardown_mock_clusters(mock_cluster_names)


@pytest.fixture(autouse=True)
def mock_openstack_manager(mocker):
    mocker.patch("openstack.connect", return_value=OpenStackConnectionMock())
