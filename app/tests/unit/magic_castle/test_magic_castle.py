from models.magic_castle.magic_castle import MagicCastle
from models.magic_castle.cluster_status_code import ClusterStatusCode
from models.magic_castle.plan_type import PlanType
from exceptions.invalid_usage_exception import ClusterNotFoundException
from tests.test_helpers import *  # noqa;
from tests.mocks.configuration.config_mock import config_auth_none_mock  # noqa;
import pytest
from exceptions.server_exception import PlanException
from subprocess import CalledProcessError

VALID_CLUSTER_CONFIGURATION = {
    "cluster_name": "a-123-45",
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
    "domain": "calculquebec.cloud",
    "public_keys": [""],
    "hieradata": "",
    "image": "CentOS-7-x64-2019-07",
    "os_floating_ips": ["100.101.102.103"],
}


@pytest.mark.usefixtures("fake_successful_subprocess_run")
def test_create_magic_castle_plan_valid(database_connection):
    cluster = MagicCastle("a-123-45.calculquebec.cloud")
    cluster.set_configuration(VALID_CLUSTER_CONFIGURATION)
    cluster.plan_creation()


def test_create_magic_castle_init_fail(database_connection, monkeypatch):
    def fake_run(process_args, *args, **kwargs):
        if process_args == ["terraform", "init", "-no-color", "-input=false"]:
            raise CalledProcessError(1, "terraform init")

    monkeypatch.setattr("models.magic_castle.magic_castle.run", fake_run)
    cluster = MagicCastle("a-123-45.calculquebec.cloud")
    cluster.set_configuration(VALID_CLUSTER_CONFIGURATION)
    with pytest.raises(
        PlanException, match="An error occurred while initializing Terraform."
    ):
        cluster.plan_creation()


def test_create_magic_castle_plan_fail(database_connection, monkeypatch):
    def fake_run(process_args, *args, **kwargs):
        if process_args[:5] == [
            "terraform",
            "plan",
            "-input=false",
            "-no-color",
            "-destroy=false",
        ]:
            raise CalledProcessError(1, "terraform plan")

    monkeypatch.setattr("models.magic_castle.magic_castle.run", fake_run)
    cluster = MagicCastle("a-123-45.calculquebec.cloud")
    cluster.set_configuration(VALID_CLUSTER_CONFIGURATION)
    with pytest.raises(
        PlanException, match="An error occurred while planning changes."
    ):
        cluster.plan_creation()


def test_create_magic_castle_plan_export_fail(database_connection, monkeypatch):
    def fake_run(process_args, *args, **kwargs):
        if process_args[:4] == [
            "terraform",
            "show",
            "-no-color",
            "-json",
        ]:
            raise CalledProcessError(1, "terraform show")

    monkeypatch.setattr("models.magic_castle.magic_castle.run", fake_run)
    cluster = MagicCastle("a-123-45.calculquebec.cloud")
    cluster.set_configuration(VALID_CLUSTER_CONFIGURATION)
    with pytest.raises(
        PlanException, match="An error occurred while exporting planned changes."
    ):
        cluster.plan_creation()


def test_get_status_valid(database_connection):
    created = MagicCastle("created.calculquebec.cloud")
    assert created.get_status() == ClusterStatusCode.CREATED
    buildplanning = MagicCastle("buildplanning.calculquebec.cloud")
    assert buildplanning.get_status() == ClusterStatusCode.PLAN_RUNNING
    valid1 = MagicCastle("valid1.calculquebec.cloud")
    assert valid1.get_status() == ClusterStatusCode.PROVISIONING_SUCCESS


def test_get_status_errors(database_connection):
    empty = MagicCastle("empty.calculquebec.cloud")
    assert empty.get_status() == ClusterStatusCode.BUILD_ERROR
    missingnodes = MagicCastle("missingnodes.sub.example.com")
    assert missingnodes.get_status() == ClusterStatusCode.BUILD_ERROR


def test_get_status_not_found(database_connection):
    magic_castle1 = MagicCastle("nonexisting")
    assert magic_castle1.get_status() == ClusterStatusCode.NOT_FOUND
    magic_castle2 = MagicCastle()
    assert magic_castle2.get_status() == ClusterStatusCode.NOT_FOUND


def test_get_plan_type_build(database_connection):
    build_planning = MagicCastle("buildplanning.calculquebec.cloud")
    assert build_planning.get_plan_type() == PlanType.BUILD
    created = MagicCastle("created.calculquebec.cloud")
    assert created.get_plan_type() == PlanType.BUILD


def test_get_plan_type_destroy(database_connection):
    magic_castle = MagicCastle("valid1.calculquebec.cloud")
    assert magic_castle.get_plan_type() == PlanType.DESTROY


def test_get_plan_type_none(database_connection):
    magic_castle = MagicCastle("missingfloatingips.c3.ca")
    assert magic_castle.get_plan_type() == PlanType.NONE


def test_get_owner_valid(database_connection):
    magic_castle = MagicCastle("missingfloatingips.c3.ca")
    assert magic_castle.get_owner() == "bob12.bobby@computecanada.ca"


def test_get_owner_no_owner(database_connection):
    magic_castle = MagicCastle("noowner.calculquebec.cloud")
    assert magic_castle.get_owner() == None


def test_dump_configuration_valid(database_connection):
    magic_castle = MagicCastle("valid1.calculquebec.cloud")
    assert magic_castle.dump_configuration(planned_only=True) == {
        "cluster_name": "valid1",
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
        "domain": "calculquebec.cloud",
        "hieradata": "",
        "public_keys": [""],
        "image": "CentOS-7-x64-2019-07",
        "os_floating_ips": ["100.101.102.103"],
    }
    assert magic_castle.dump_configuration(planned_only=False) == {
        "cluster_name": "valid1",
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
        "domain": "calculquebec.cloud",
        "hieradata": "",
        "public_keys": ["ssh-rsa FAKE"],
        "image": "CentOS-7-x64-2019-07",
        "os_floating_ips": ["100.101.102.103"],
    }


def test_dump_configuration_empty(database_connection):
    magic_castle = MagicCastle("empty.calculquebec.cloud")
    assert magic_castle.dump_configuration() == dict()


def test_dump_configuration_missing_nodes(database_connection):
    magic_castle = MagicCastle("missingnodes.sub.example.com")
    assert magic_castle.dump_configuration(planned_only=True) == {
        "cluster_name": "missingnodes",
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
        "domain": "sub.example.com",
        "hieradata": "",
        "public_keys": [""],
        "image": "CentOS-7-x64-2019-07",
        "os_floating_ips": ["100.101.102.103"],
    }
    assert magic_castle.dump_configuration(planned_only=False) == {
        "cluster_name": "missingnodes",
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
        "domain": "sub.example.com",
        "hieradata": "",
        "public_keys": ["ssh-rsa FAKE"],
        "image": "CentOS-7-x64-2019-07",
        "os_floating_ips": ["100.101.102.103"],
    }


def test_dump_configuration_busy(database_connection):
    magic_castle = MagicCastle("missingfloatingips.c3.ca")
    assert magic_castle.dump_configuration() == {
        "cluster_name": "missingfloatingips",
        "domain": "c3.ca",
        "image": "CentOS-7-x64-2019-07",
        "nb_users": 17,
        "instances": {
            "mgmt": {"type": "p4-6gb", "count": 1},
            "login": {"type": "p4-6gb", "count": 1},
            "node": {"type": "p2-3gb", "count": 3},
        },
        "storage": {
            "type": "nfs",
            "home_size": 50,
            "project_size": 1,
            "scratch_size": 1,
        },
        "public_keys": [""],
        "hieradata": "",
        "guest_passwd": "password-123",
        "os_floating_ips": ["Automatic allocation"],
    }


def test_dump_configuration_not_found(database_connection):
    magic_castle = MagicCastle()
    with pytest.raises(ClusterNotFoundException):
        magic_castle.dump_configuration()


def test_get_available_resources_valid(database_connection):
    """
    Mock context :

    valid1 cluster uses:
    1 + 1 + 1 = 3 instances
    4 + 4 + 2 = 10 vcpus
    6144 + 6144 + 3072 = 15360 ram (15 GiO)
    3 [root disks] + 3 [external volumes] = 6 volumes
    10 + 10 + 10 [root disks]
    + 50 + 50 + 100 [external volumes] = 230 GiO of volume storage

    openstack's quotas says there currently remains:
    128 - 28 = 100 instances
    500 - 199 = 301 vcpus
    286,720 - 184,320 = 102,400 ram (100 GiO)
    128 - 100 = 28 volumes
    1000 - 720 = 280 GiO of volume storage

    Therefore, valid1 cluster can use a total of:
    3 + 100 = 103 instances
    10 + 301 = 311 vcpus
    15,360 + 102,400 = 117,760 ram (115 GiO)
    6 + 28 = 34 volumes
    230 + 280 = 510 GiO of volume storage
    """
    magic_castle = MagicCastle("valid1.calculquebec.cloud")
    assert magic_castle.get_available_resources() == {
        "quotas": {
            "instance_count": {"max": 103},
            "ram": {"max": 117_760},
            "vcpus": {"max": 311},
            "volume_count": {"max": 34},
            "volume_size": {"max": 510},
        },
        "resource_details": {
            "instance_types": [
                {
                    "name": "p1-1.5gb",
                    "vcpus": 1,
                    "ram": 1_536,
                    "required_volume_count": 1,
                    "required_volume_size": 10,
                },
                {
                    "name": "p2-3gb",
                    "vcpus": 2,
                    "ram": 3_072,
                    "required_volume_count": 1,
                    "required_volume_size": 10,
                },
                {
                    "name": "p4-6gb",
                    "vcpus": 4,
                    "ram": 6_144,
                    "required_volume_count": 1,
                    "required_volume_size": 10,
                },
                {
                    "name": "c8-30gb-186",
                    "vcpus": 8,
                    "ram": 30_720,
                    "required_volume_count": 0,
                    "required_volume_size": 0,
                },
                {
                    "name": "c8-90gb-186",
                    "vcpus": 8,
                    "ram": 92_160,
                    "required_volume_count": 0,
                    "required_volume_size": 0,
                },
                {
                    "name": "g2-c24-112gb-500",
                    "vcpus": 24,
                    "ram": 114_688,
                    "required_volume_count": 0,
                    "required_volume_size": 0,
                },
                {
                    "name": "c16-120gb-392",
                    "vcpus": 16,
                    "ram": 122_880,
                    "required_volume_count": 0,
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
                "Automatic allocation",
                "100.101.102.103",
                "2.1.1.1",
                "2.1.1.2",
                "2.1.1.3",
            ],
            "storage": {"type": ["nfs"]},
            "domain": ["calculquebec.cloud", "c3.ca", "sub.example.com"],
        },
    }


def test_get_available_resources_empty(database_connection):
    """
    Mock context :

    empty cluster uses 0 vcpus, 0 ram, 0 volume

    openstack's quotas says there currently remains:
    128 - 28 = 100 instances
    500 - 199 = 301 vcpus
    286,720 - 184,320 = 102,400 ram (100 GiO)
    128 - 100 = 28 volumes
    1000 - 720 = 280 GiO of volume storage
    """
    magic_castle = MagicCastle("empty.calculquebec.cloud")
    assert magic_castle.get_available_resources() == {
        "quotas": {
            "instance_count": {"max": 100},
            "ram": {"max": 102_400},
            "vcpus": {"max": 301},
            "volume_count": {"max": 28},
            "volume_size": {"max": 280},
        },
        "resource_details": {
            "instance_types": [
                {
                    "name": "p1-1.5gb",
                    "vcpus": 1,
                    "ram": 1_536,
                    "required_volume_count": 1,
                    "required_volume_size": 10,
                },
                {
                    "name": "p2-3gb",
                    "vcpus": 2,
                    "ram": 3_072,
                    "required_volume_count": 1,
                    "required_volume_size": 10,
                },
                {
                    "name": "p4-6gb",
                    "vcpus": 4,
                    "ram": 6_144,
                    "required_volume_count": 1,
                    "required_volume_size": 10,
                },
                {
                    "name": "c8-30gb-186",
                    "vcpus": 8,
                    "ram": 30_720,
                    "required_volume_count": 0,
                    "required_volume_size": 0,
                },
                {
                    "name": "c8-90gb-186",
                    "vcpus": 8,
                    "ram": 92_160,
                    "required_volume_count": 0,
                    "required_volume_size": 0,
                },
                {
                    "name": "g2-c24-112gb-500",
                    "vcpus": 24,
                    "ram": 114_688,
                    "required_volume_count": 0,
                    "required_volume_size": 0,
                },
                {
                    "name": "c16-120gb-392",
                    "vcpus": 16,
                    "ram": 122_880,
                    "required_volume_count": 0,
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
                "Automatic allocation",
                "2.1.1.1",
                "2.1.1.2",
                "2.1.1.3",
            ],
            "storage": {"type": ["nfs"]},
            "domain": ["calculquebec.cloud", "c3.ca", "sub.example.com"],
        },
    }


def test_get_available_resources_missing_nodes(database_connection):
    """
    Mock context :

    missingnodes cluster uses
    0 instance
    0 vcpus
    0 ram
    0 [root disks] + 3 [external volumes] = 3 volumes
    0 + 0 + 0 [root disks]
    + 50 + 50 + 100 [external volumes] = 200 GiO of volume storage

    openstack's quotas says there currently remains:
    128 - 28 = 100 instances
    500 - 199 = 301 vcpus
    286,720 - 184,320 = 102,400 ram (100 GiO)
    128 - 100 = 28 volumes
    1000 - 720 = 280 GiO of volume storage

    Therefore, missingnodes cluster can use a total of:
    0 + 100 = 0 instances
    0 + 301 = 301 vcpus
    0 + 102,400 = 102,400 ram (100 GiO)
    3 + 28 = 31 volumes
    200 + 280 = 480 GiO of volume storage
    """
    magic_castle = MagicCastle("missingnodes.sub.example.com")
    assert magic_castle.get_available_resources() == {
        "quotas": {
            "instance_count": {"max": 100},
            "ram": {"max": 102_400},
            "vcpus": {"max": 301},
            "volume_count": {"max": 31},
            "volume_size": {"max": 480},
        },
        "resource_details": {
            "instance_types": [
                {
                    "name": "p1-1.5gb",
                    "vcpus": 1,
                    "ram": 1_536,
                    "required_volume_count": 1,
                    "required_volume_size": 10,
                },
                {
                    "name": "p2-3gb",
                    "vcpus": 2,
                    "ram": 3_072,
                    "required_volume_count": 1,
                    "required_volume_size": 10,
                },
                {
                    "name": "p4-6gb",
                    "vcpus": 4,
                    "ram": 6_144,
                    "required_volume_count": 1,
                    "required_volume_size": 10,
                },
                {
                    "name": "c8-30gb-186",
                    "vcpus": 8,
                    "ram": 30_720,
                    "required_volume_count": 0,
                    "required_volume_size": 0,
                },
                {
                    "name": "c8-90gb-186",
                    "vcpus": 8,
                    "ram": 92_160,
                    "required_volume_count": 0,
                    "required_volume_size": 0,
                },
                {
                    "name": "g2-c24-112gb-500",
                    "vcpus": 24,
                    "ram": 114_688,
                    "required_volume_count": 0,
                    "required_volume_size": 0,
                },
                {
                    "name": "c16-120gb-392",
                    "vcpus": 16,
                    "ram": 122_880,
                    "required_volume_count": 0,
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
                "Automatic allocation",
                "100.101.102.103",
                "2.1.1.1",
                "2.1.1.2",
                "2.1.1.3",
            ],
            "storage": {"type": ["nfs"]},
            "domain": ["calculquebec.cloud", "c3.ca", "sub.example.com"],
        },
    }


def test_get_available_resources_not_found(database_connection):
    """
    Mock context :

    openstack's quotas says there currently remains:
    128 - 28 = 100 instances
    500 - 199 = 301 vcpus
    286,720 - 184,320 = 102,400 ram (100 GiO)
    128 - 100 = 28 volumes
    1000 - 720 = 280 GiO of volume storage
    """
    magic_castle = MagicCastle()
    assert magic_castle.get_available_resources() == {
        "quotas": {
            "instance_count": {"max": 100},
            "ram": {"max": 102_400},
            "vcpus": {"max": 301},
            "volume_count": {"max": 28},
            "volume_size": {"max": 280},
        },
        "resource_details": {
            "instance_types": [
                {
                    "name": "p1-1.5gb",
                    "vcpus": 1,
                    "ram": 1_536,
                    "required_volume_count": 1,
                    "required_volume_size": 10,
                },
                {
                    "name": "p2-3gb",
                    "vcpus": 2,
                    "ram": 3_072,
                    "required_volume_count": 1,
                    "required_volume_size": 10,
                },
                {
                    "name": "p4-6gb",
                    "vcpus": 4,
                    "ram": 6_144,
                    "required_volume_count": 1,
                    "required_volume_size": 10,
                },
                {
                    "name": "c8-30gb-186",
                    "vcpus": 8,
                    "ram": 30_720,
                    "required_volume_count": 0,
                    "required_volume_size": 0,
                },
                {
                    "name": "c8-90gb-186",
                    "vcpus": 8,
                    "ram": 92_160,
                    "required_volume_count": 0,
                    "required_volume_size": 0,
                },
                {
                    "name": "g2-c24-112gb-500",
                    "vcpus": 24,
                    "ram": 114_688,
                    "required_volume_count": 0,
                    "required_volume_size": 0,
                },
                {
                    "name": "c16-120gb-392",
                    "vcpus": 16,
                    "ram": 122_880,
                    "required_volume_count": 0,
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
                "Automatic allocation",
                "2.1.1.1",
                "2.1.1.2",
                "2.1.1.3",
            ],
            "storage": {"type": ["nfs"]},
            "domain": ["calculquebec.cloud", "c3.ca", "sub.example.com"],
        },
    }
