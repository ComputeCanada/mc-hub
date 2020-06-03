from models.magic_castle import MagicCastle
from models.cluster_status_code import ClusterStatusCode
from exceptions.cluster_not_found_exception import ClusterNotFoundException
from tests.mocks.openstack.openstack_connection_mock import OpenStackConnectionMock
from pathlib import Path
from os import path
from shutil import rmtree, copytree
import pytest


def setup_mock_clusters(cluster_names):
    for cluster_name in cluster_names:
        copytree(
            path.join(Path(__file__).parent.parent, "mock-clusters", cluster_name),
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
    mocker.patch(
        "models.openstack_manager.OpenStackManager._OpenStackManager__get_compute_quotas",
        return_value={
            "cores": {"limit": 500, "in_use": 199},
            "ram": {"limit": 280_000, "in_use": 180_000},
        },
    )
    mocker.patch(
        "models.openstack_manager.OpenStackManager._OpenStackManager__get_volume_quotas",
        return_value={"gigabytes": {"limit": 1000, "in_use": 720}},
    )
    mocker.patch(
        "models.openstack_manager.OpenStackManager._OpenStackManager__get_network_quotas",
        return_value={"floatingip": {"limit": 5, "used": 3}},
    )
    mocker.patch("openstack.connect", return_value=OpenStackConnectionMock())


def test_get_status_valid():
    magic_castle = MagicCastle("valid-1")
    assert magic_castle.get_status() == ClusterStatusCode.BUILD_SUCCESS


def test_get_status_empty():
    magic_castle = MagicCastle("empty")
    assert magic_castle.get_status() == ClusterStatusCode.BUILD_ERROR


def test_get_status_missing_nodes():
    magic_castle = MagicCastle("missing-nodes")
    assert magic_castle.get_status() == ClusterStatusCode.BUILD_ERROR


def test_get_status_not_found():
    magic_castle1 = MagicCastle("non-existing")
    assert magic_castle1.get_status() == ClusterStatusCode.NOT_FOUND
    magic_castle2 = MagicCastle()
    assert magic_castle2.get_status() == ClusterStatusCode.NOT_FOUND


def test_get_state_valid():
    magic_castle = MagicCastle("valid-1")
    assert magic_castle.get_state() == {
        "cluster_name": "valid-1",
        "nb_users": 10,
        "guest_passwd": "password-123",
        "storage": {
            "type": "nfs",
            "home_size": 100,
            "scratch_size": 50,
            "project_size": 50,
        },
        "instances": {
            "mgmt": {"type": "p4-6gb", "count": 1},
            "login": {"type": "p4-6gb", "count": 1},
            "node": {"type": "p2-3gb", "count": 1},
        },
        "domain": "example.com",
        "public_keys": ["ssh-rsa FAKE"],
        "image": "CentOS-7-x64-2019-07",
        "os_floating_ips": ["100.101.102.103"],
    }


def test_get_state_empty():
    magic_castle = MagicCastle("empty")
    assert magic_castle.get_state() == {
        "cluster_name": "empty",
        "domain": "",
        "image": "",
        "nb_users": 0,
        "instances": {
            "mgmt": {"type": "", "count": 0},
            "login": {"type": "", "count": 0},
            "node": {"type": "", "count": 0},
        },
        "storage": {
            "type": "nfs",
            "home_size": 0,
            "project_size": 0,
            "scratch_size": 0,
        },
        "public_keys": [],
        "guest_passwd": "",
        "os_floating_ips": [],
    }


def test_get_state_missing_nodes():
    magic_castle = MagicCastle("missing-nodes")
    assert magic_castle.get_state() == {
        "cluster_name": "missing-nodes",
        "nb_users": 10,
        "guest_passwd": "password-123",
        "storage": {
            "type": "nfs",
            "home_size": 100,
            "scratch_size": 50,
            "project_size": 50,
        },
        "instances": {
            "mgmt": {"type": "", "count": 0},
            "login": {"type": "", "count": 0},
            "node": {"type": "", "count": 0},
        },
        "domain": "example.com",
        "public_keys": ["ssh-rsa FAKE"],
        "image": "CentOS-7-x64-2019-07",
        "os_floating_ips": ["100.101.102.103"],
    }


def test_get_state_not_found():
    magic_castle = MagicCastle()
    with pytest.raises(ClusterNotFoundException):
        magic_castle.get_state()


def test_get_available_resources_valid():
    """
    Mock context :

    valid-1 cluster uses:
    4 + 4 + 2 = 10 vcpus
    6144 + 6144 + 3072 = 15360 ram (15 gb)
    10 + 10 + 10 [root disks]
    + 50 + 50 + 100 [external volumes] = 230 gb of volume storage

    openstack's quotas says there currently remains:
    500 - 199 = 301 vcpus
    280000 - 180000 = 100000 ram (100 gb)
    1000 - 720 = 280 gb

    Therefore, valid-1 cluster can use a total of:
    10 + 301 = 311 vcpus
    15360 + 100000 = 115360 ram (115 gb)
    230 + 280 = 510 gb of volume storage
    """
    magic_castle = MagicCastle("valid-1")
    assert magic_castle.get_available_resources() == {
        "quotas": {
            "ram": {"max": 115_360},
            "vcpus": {"max": 311},
            "volume_size": {"max": 510},
        },
        "resource_details": {
            "instance_types": [
                {
                    "name": "p1-1.5gb",
                    "vcpus": 1,
                    "ram": 1_500,
                    "required_volume_size": 10,
                },
                {
                    "name": "c8-30gb-186",
                    "vcpus": 8,
                    "ram": 30_000,
                    "required_volume_size": 0,
                },
                {
                    "name": "c8-90gb-186",
                    "vcpus": 8,
                    "ram": 90_000,
                    "required_volume_size": 0,
                },
                {
                    "name": "g2-c24-112gb-500",
                    "vcpus": 24,
                    "ram": 112_000,
                    "required_volume_size": 0,
                },
                {
                    "name": "c16-120gb-392",
                    "vcpus": 16,
                    "ram": 120_000,
                    "required_volume_size": 0,
                },
            ]
        },
        "possible_resources": {
            "image": ["centos7", "CentOS-8 x64", "CentOS VGPU"],
            "instances": {
                "mgmt": {
                    "type": [
                        "c8-30gb-186",
                        "c8-90gb-186",
                        "g2-c24-112gb-500",
                        "c16-120gb-392",
                    ]
                },
                "login": {
                    "type": [
                        "c8-30gb-186",
                        "c8-90gb-186",
                        "g2-c24-112gb-500",
                        "c16-120gb-392",
                    ]
                },
                "node": {
                    "type": [
                        "c8-30gb-186",
                        "c8-90gb-186",
                        "g2-c24-112gb-500",
                        "c16-120gb-392",
                    ]
                },
            },
            "os_floating_ips": [
                "100.101.102.103",
                "2.1.1.1",
                "2.1.1.2",
                "2.1.1.3",
                "Automatic allocation",
            ],
            "storage": {"type": ["nfs"]},
        },
    }


def test_get_available_resources_empty():
    """
    Mock context :

    empty cluster uses 0 vcpus and 0 ram

    openstack's quotas says there currently remains:
    500 - 199 = 301 vcpus
    280000 - 180000 = 100000 ram (100 gb)
    1000 - 720 = 280 gb
    """
    magic_castle = MagicCastle("empty")
    assert magic_castle.get_available_resources() == {
        "quotas": {
            "ram": {"max": 100_000},
            "vcpus": {"max": 301},
            "volume_size": {"max": 280},
        },
        "resource_details": {
            "instance_types": [
                {
                    "name": "p1-1.5gb",
                    "vcpus": 1,
                    "ram": 1_500,
                    "required_volume_size": 10,
                },
                {
                    "name": "c8-30gb-186",
                    "vcpus": 8,
                    "ram": 30_000,
                    "required_volume_size": 0,
                },
                {
                    "name": "c8-90gb-186",
                    "vcpus": 8,
                    "ram": 90_000,
                    "required_volume_size": 0,
                },
                {
                    "name": "g2-c24-112gb-500",
                    "vcpus": 24,
                    "ram": 112_000,
                    "required_volume_size": 0,
                },
                {
                    "name": "c16-120gb-392",
                    "vcpus": 16,
                    "ram": 120_000,
                    "required_volume_size": 0,
                },
            ]
        },
        "possible_resources": {
            "image": ["centos7", "CentOS-8 x64", "CentOS VGPU"],
            "instances": {
                "mgmt": {
                    "type": [
                        "c8-30gb-186",
                        "c8-90gb-186",
                        "g2-c24-112gb-500",
                        "c16-120gb-392",
                    ]
                },
                "login": {
                    "type": [
                        "c8-30gb-186",
                        "c8-90gb-186",
                        "g2-c24-112gb-500",
                        "c16-120gb-392",
                    ]
                },
                "node": {
                    "type": [
                        "c8-30gb-186",
                        "c8-90gb-186",
                        "g2-c24-112gb-500",
                        "c16-120gb-392",
                    ]
                },
            },
            "os_floating_ips": [
                "2.1.1.1",
                "2.1.1.2",
                "2.1.1.3",
                "Automatic allocation",
            ],
            "storage": {"type": ["nfs"]},
        },
    }


def test_get_available_resources_missing_nodes():
    """
    Mock context :

    missing-nodes cluster uses
    0 vcpus
    0 ram
    0 + 0 + 0 [root disks]
    + 50 + 50 + 100 [external volumes] = 200 gb of volume storage

    openstack's quotas says there currently remains:
    500 - 199 = 301 vcpus
    280000 - 180000 = 100000 ram (100 gb)
    1000 - 720 = 280 gb

    Therefore, missing-nodes cluster can use a total of:
    0 + 301 = 301 vcpus
    0 + 100000 = 100000 ram (100 gb)
    200 + 280 = 480 gb of volume storage
    """
    magic_castle = MagicCastle("missing-nodes")
    assert magic_castle.get_available_resources() == {
        "quotas": {
            "ram": {"max": 100_000},
            "vcpus": {"max": 301},
            "volume_size": {"max": 480},
        },
        "resource_details": {
            "instance_types": [
                {
                    "name": "p1-1.5gb",
                    "vcpus": 1,
                    "ram": 1_500,
                    "required_volume_size": 10,
                },
                {
                    "name": "c8-30gb-186",
                    "vcpus": 8,
                    "ram": 30_000,
                    "required_volume_size": 0,
                },
                {
                    "name": "c8-90gb-186",
                    "vcpus": 8,
                    "ram": 90_000,
                    "required_volume_size": 0,
                },
                {
                    "name": "g2-c24-112gb-500",
                    "vcpus": 24,
                    "ram": 112_000,
                    "required_volume_size": 0,
                },
                {
                    "name": "c16-120gb-392",
                    "vcpus": 16,
                    "ram": 120_000,
                    "required_volume_size": 0,
                },
            ]
        },
        "possible_resources": {
            "image": ["centos7", "CentOS-8 x64", "CentOS VGPU"],
            "instances": {
                "mgmt": {
                    "type": [
                        "c8-30gb-186",
                        "c8-90gb-186",
                        "g2-c24-112gb-500",
                        "c16-120gb-392",
                    ]
                },
                "login": {
                    "type": [
                        "c8-30gb-186",
                        "c8-90gb-186",
                        "g2-c24-112gb-500",
                        "c16-120gb-392",
                    ]
                },
                "node": {
                    "type": [
                        "c8-30gb-186",
                        "c8-90gb-186",
                        "g2-c24-112gb-500",
                        "c16-120gb-392",
                    ]
                },
            },
            "os_floating_ips": [
                "100.101.102.103",
                "2.1.1.1",
                "2.1.1.2",
                "2.1.1.3",
                "Automatic allocation",
            ],
            "storage": {"type": ["nfs"]},
        },
    }


def test_get_available_resources_not_found():
    """
    Mock context :

    openstack's quotas says there currently remains:
    500 - 199 = 301 vcpus
    280000 - 180000 = 100000 ram (100 gb)
    1000 - 720 = 280 gb
    """
    magic_castle = MagicCastle()
    assert magic_castle.get_available_resources() == {
        "quotas": {
            "ram": {"max": 100_000},
            "vcpus": {"max": 301},
            "volume_size": {"max": 280},
        },
        "resource_details": {
            "instance_types": [
                {
                    "name": "p1-1.5gb",
                    "vcpus": 1,
                    "ram": 1_500,
                    "required_volume_size": 10,
                },
                {
                    "name": "c8-30gb-186",
                    "vcpus": 8,
                    "ram": 30_000,
                    "required_volume_size": 0,
                },
                {
                    "name": "c8-90gb-186",
                    "vcpus": 8,
                    "ram": 90_000,
                    "required_volume_size": 0,
                },
                {
                    "name": "g2-c24-112gb-500",
                    "vcpus": 24,
                    "ram": 112_000,
                    "required_volume_size": 0,
                },
                {
                    "name": "c16-120gb-392",
                    "vcpus": 16,
                    "ram": 120_000,
                    "required_volume_size": 0,
                },
            ]
        },
        "possible_resources": {
            "image": ["centos7", "CentOS-8 x64", "CentOS VGPU"],
            "instances": {
                "mgmt": {
                    "type": [
                        "c8-30gb-186",
                        "c8-90gb-186",
                        "g2-c24-112gb-500",
                        "c16-120gb-392",
                    ]
                },
                "login": {
                    "type": [
                        "c8-30gb-186",
                        "c8-90gb-186",
                        "g2-c24-112gb-500",
                        "c16-120gb-392",
                    ]
                },
                "node": {
                    "type": [
                        "c8-30gb-186",
                        "c8-90gb-186",
                        "g2-c24-112gb-500",
                        "c16-120gb-392",
                    ]
                },
            },
            "os_floating_ips": [
                "2.1.1.1",
                "2.1.1.2",
                "2.1.1.3",
                "Automatic allocation",
            ],
            "storage": {"type": ["nfs"]},
        },
    }
