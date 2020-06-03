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
            "ram": {"limit": 286_720, "in_use": 184_320},  # 280 GiO limit, 180 GiO used
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
    6144 + 6144 + 3072 = 15360 ram (15 GiO)
    10 + 10 + 10 [root disks]
    + 50 + 50 + 100 [external volumes] = 230 GiO of volume storage

    openstack's quotas says there currently remains:
    500 - 199 = 301 vcpus
    286,720 - 184,320 = 102,400 ram (100 GiO)
    1000 - 720 = 280 GiO of volume storage

    Therefore, valid-1 cluster can use a total of:
    10 + 301 = 311 vcpus
    15,360 + 102,400 = 117,760 ram (115 GiO)
    230 + 280 = 510 GiO of volume storage
    """
    magic_castle = MagicCastle("valid-1")
    assert magic_castle.get_available_resources() == {
        "quotas": {
            "ram": {"max": 117_760},
            "vcpus": {"max": 311},
            "volume_size": {"max": 510},
        },
        "resource_details": {
            "instance_types": [
                {
                    "name": "p1-1.5gb",
                    "vcpus": 1,
                    "ram": 1_536,
                    "required_volume_size": 10,
                },
                {
                    "name": "p2-3gb",
                    "vcpus": 2,
                    "ram": 3_072,
                    "required_volume_size": 10,
                },
                {
                    "name": "p4-6gb",
                    "vcpus": 4,
                    "ram": 6_144,
                    "required_volume_size": 10,
                },
                {
                    "name": "c8-30gb-186",
                    "vcpus": 8,
                    "ram": 30_720,
                    "required_volume_size": 0,
                },
                {
                    "name": "c8-90gb-186",
                    "vcpus": 8,
                    "ram": 92_160,
                    "required_volume_size": 0,
                },
                {
                    "name": "g2-c24-112gb-500",
                    "vcpus": 24,
                    "ram": 114_688,
                    "required_volume_size": 0,
                },
                {
                    "name": "c16-120gb-392",
                    "vcpus": 16,
                    "ram": 122_880,
                    "required_volume_size": 0,
                },
            ]
        },
        "possible_resources": {
            "image": ["centos7", "CentOS-8 x64", "CentOS VGPU"],
            "instances": {
                "mgmt": {
                    "type": [
                        "p4-6gb",
                        "c8-30gb-186",
                        "c8-90gb-186",
                        "g2-c24-112gb-500",
                        "c16-120gb-392",
                    ]
                },
                "login": {
                    "type": [
                        "p2-3gb",
                        "p4-6gb",
                        "c8-30gb-186",
                        "c8-90gb-186",
                        "g2-c24-112gb-500",
                        "c16-120gb-392",
                    ]
                },
                "node": {
                    "type": [
                        "p2-3gb",
                        "p4-6gb",
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
    286,720 - 184,320 = 102,400 ram (100 GiO)
    1000 - 720 = 280 GiO of volume storage
    """
    magic_castle = MagicCastle("empty")
    assert magic_castle.get_available_resources() == {
        "quotas": {
            "ram": {"max": 102_400},
            "vcpus": {"max": 301},
            "volume_size": {"max": 280},
        },
        "resource_details": {
            "instance_types": [
                {
                    "name": "p1-1.5gb",
                    "vcpus": 1,
                    "ram": 1_536,
                    "required_volume_size": 10,
                },
                {
                    "name": "p2-3gb",
                    "vcpus": 2,
                    "ram": 3_072,
                    "required_volume_size": 10,
                },
                {
                    "name": "p4-6gb",
                    "vcpus": 4,
                    "ram": 6_144,
                    "required_volume_size": 10,
                },
                {
                    "name": "c8-30gb-186",
                    "vcpus": 8,
                    "ram": 30_720,
                    "required_volume_size": 0,
                },
                {
                    "name": "c8-90gb-186",
                    "vcpus": 8,
                    "ram": 92_160,
                    "required_volume_size": 0,
                },
                {
                    "name": "g2-c24-112gb-500",
                    "vcpus": 24,
                    "ram": 114_688,
                    "required_volume_size": 0,
                },
                {
                    "name": "c16-120gb-392",
                    "vcpus": 16,
                    "ram": 122_880,
                    "required_volume_size": 0,
                },
            ]
        },
        "possible_resources": {
            "image": ["centos7", "CentOS-8 x64", "CentOS VGPU"],
            "instances": {
                "mgmt": {
                    "type": [
                        "p4-6gb",
                        "c8-30gb-186",
                        "c8-90gb-186",
                        "g2-c24-112gb-500",
                        "c16-120gb-392",
                    ]
                },
                "login": {
                    "type": [
                        "p2-3gb",
                        "p4-6gb",
                        "c8-30gb-186",
                        "c8-90gb-186",
                        "g2-c24-112gb-500",
                        "c16-120gb-392",
                    ]
                },
                "node": {
                    "type": [
                        "p2-3gb",
                        "p4-6gb",
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
    + 50 + 50 + 100 [external volumes] = 200 GiO of volume storage

    openstack's quotas says there currently remains:
    500 - 199 = 301 vcpus
    286,720 - 184,320 = 102,400 ram (100 GiO)
    1000 - 720 = 280 GiO of volume storage

    Therefore, missing-nodes cluster can use a total of:
    0 + 301 = 301 vcpus
    0 + 102,400 = 102,400 ram (100 GiO)
    200 + 280 = 480 GiO of volume storage
    """
    magic_castle = MagicCastle("missing-nodes")
    assert magic_castle.get_available_resources() == {
        "quotas": {
            "ram": {"max": 102_400},
            "vcpus": {"max": 301},
            "volume_size": {"max": 480},
        },
        "resource_details": {
            "instance_types": [
                {
                    "name": "p1-1.5gb",
                    "vcpus": 1,
                    "ram": 1_536,
                    "required_volume_size": 10,
                },
                {
                    "name": "p2-3gb",
                    "vcpus": 2,
                    "ram": 3_072,
                    "required_volume_size": 10,
                },
                {
                    "name": "p4-6gb",
                    "vcpus": 4,
                    "ram": 6_144,
                    "required_volume_size": 10,
                },
                {
                    "name": "c8-30gb-186",
                    "vcpus": 8,
                    "ram": 30_720,
                    "required_volume_size": 0,
                },
                {
                    "name": "c8-90gb-186",
                    "vcpus": 8,
                    "ram": 92_160,
                    "required_volume_size": 0,
                },
                {
                    "name": "g2-c24-112gb-500",
                    "vcpus": 24,
                    "ram": 114_688,
                    "required_volume_size": 0,
                },
                {
                    "name": "c16-120gb-392",
                    "vcpus": 16,
                    "ram": 122_880,
                    "required_volume_size": 0,
                },
            ]
        },
        "possible_resources": {
            "image": ["centos7", "CentOS-8 x64", "CentOS VGPU"],
            "instances": {
                "mgmt": {
                    "type": [
                        "p4-6gb",
                        "c8-30gb-186",
                        "c8-90gb-186",
                        "g2-c24-112gb-500",
                        "c16-120gb-392",
                    ]
                },
                "login": {
                    "type": [
                        "p2-3gb",
                        "p4-6gb",
                        "c8-30gb-186",
                        "c8-90gb-186",
                        "g2-c24-112gb-500",
                        "c16-120gb-392",
                    ]
                },
                "node": {
                    "type": [
                        "p2-3gb",
                        "p4-6gb",
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
    286,720 - 184,320 = 102,400 ram (100 GiO)
    1000 - 720 = 280 GiO of volume storage
    """
    magic_castle = MagicCastle()
    assert magic_castle.get_available_resources() == {
        "quotas": {
            "ram": {"max": 102_400},
            "vcpus": {"max": 301},
            "volume_size": {"max": 280},
        },
        "resource_details": {
            "instance_types": [
                {
                    "name": "p1-1.5gb",
                    "vcpus": 1,
                    "ram": 1_536,
                    "required_volume_size": 10,
                },
                {
                    "name": "p2-3gb",
                    "vcpus": 2,
                    "ram": 3_072,
                    "required_volume_size": 10,
                },
                {
                    "name": "p4-6gb",
                    "vcpus": 4,
                    "ram": 6_144,
                    "required_volume_size": 10,
                },
                {
                    "name": "c8-30gb-186",
                    "vcpus": 8,
                    "ram": 30_720,
                    "required_volume_size": 0,
                },
                {
                    "name": "c8-90gb-186",
                    "vcpus": 8,
                    "ram": 92_160,
                    "required_volume_size": 0,
                },
                {
                    "name": "g2-c24-112gb-500",
                    "vcpus": 24,
                    "ram": 114_688,
                    "required_volume_size": 0,
                },
                {
                    "name": "c16-120gb-392",
                    "vcpus": 16,
                    "ram": 122_880,
                    "required_volume_size": 0,
                },
            ]
        },
        "possible_resources": {
            "image": ["centos7", "CentOS-8 x64", "CentOS VGPU"],
            "instances": {
                "mgmt": {
                    "type": [
                        "p4-6gb",
                        "c8-30gb-186",
                        "c8-90gb-186",
                        "g2-c24-112gb-500",
                        "c16-120gb-392",
                    ]
                },
                "login": {
                    "type": [
                        "p2-3gb",
                        "p4-6gb",
                        "c8-30gb-186",
                        "c8-90gb-186",
                        "g2-c24-112gb-500",
                        "c16-120gb-392",
                    ]
                },
                "node": {
                    "type": [
                        "p2-3gb",
                        "p4-6gb",
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
