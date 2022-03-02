import pytest

from copy import deepcopy
from subprocess import CalledProcessError

from mchub.models.constants import DEFAULT_CLOUD
from mchub.models.magic_castle.magic_castle import MagicCastle
from mchub.models.magic_castle.cluster_status_code import ClusterStatusCode
from mchub.models.magic_castle.plan_type import PlanType
from mchub.exceptions.invalid_usage_exception import ClusterNotFoundException
from mchub.exceptions.server_exception import PlanException

from ... test_helpers import *  # noqa;
from ... mocks.configuration.config_mock import config_auth_none_mock  # noqa;


VALID_CLUSTER_CONFIGURATION = {
    "cloud_id": DEFAULT_CLOUD,
    "cluster_name": "a-123-45",
    "nb_users": 10,
    "guest_passwd": "password-123",
    "volumes": {
        "nfs": {
            "home": {"size": 100},
            "scratch": {"size": 50},
            "project": {"size": 50},
        }
    },
    "instances": {
        "mgmt": {"type": "p4-6gb", "count": 1, "tags": ["mgmt", "puppet", "nfs"]},
        "login": {"type": "p4-6gb", "count": 1, "tags": ["login", "proxy", "public"]},
        "node": {"type": "p2-3gb", "count": 1, "tags": ["node"]},
    },
    "domain": "calculquebec.cloud",
    "public_keys": [""],
    "hieradata": "",
    "image": "CentOS-7-x64-2021-11",
}


@pytest.mark.usefixtures("fake_successful_subprocess_run")
def test_create_magic_castle_plan_valid(database_connection):
    cluster = MagicCastle("a-123-45.calculquebec.cloud")
    cluster.plan_creation(deepcopy(VALID_CLUSTER_CONFIGURATION))


def test_create_magic_castle_init_fail(database_connection, monkeypatch):
    def fake_run(process_args, *args, **kwargs):
        if process_args == ["terraform", "init", "-no-color", "-input=false"]:
            raise CalledProcessError(1, "terraform init")

    monkeypatch.setattr("mchub.models.magic_castle.magic_castle.run", fake_run)
    cluster = MagicCastle("a-123-45.calculquebec.cloud")
    with pytest.raises(
        PlanException, match="An error occurred while initializing Terraform."
    ):
        cluster.plan_creation(deepcopy(VALID_CLUSTER_CONFIGURATION))


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

    monkeypatch.setattr("mchub.models.magic_castle.magic_castle.run", fake_run)
    cluster = MagicCastle("a-123-45.calculquebec.cloud")
    with pytest.raises(
        PlanException, match="An error occurred while planning changes."
    ):
        cluster.plan_creation(deepcopy(VALID_CLUSTER_CONFIGURATION))


def test_create_magic_castle_plan_export_fail(database_connection, monkeypatch):
    def fake_run(process_args, *args, **kwargs):
        if process_args[:4] == [
            "terraform",
            "show",
            "-no-color",
            "-json",
        ]:
            raise CalledProcessError(1, "terraform show")

    monkeypatch.setattr("mchub.models.magic_castle.magic_castle.run", fake_run)
    cluster = MagicCastle("a-123-45.calculquebec.cloud")
    with pytest.raises(
        PlanException, match="An error occurred while exporting planned changes."
    ):
        cluster.plan_creation(deepcopy(VALID_CLUSTER_CONFIGURATION))


def test_get_status_valid(database_connection):
    created = MagicCastle("created.calculquebec.cloud")
    assert created.status == ClusterStatusCode.CREATED
    buildplanning = MagicCastle("buildplanning.calculquebec.cloud")
    assert buildplanning.status == ClusterStatusCode.PLAN_RUNNING
    valid1 = MagicCastle("valid1.calculquebec.cloud")
    assert valid1.status == ClusterStatusCode.PROVISIONING_SUCCESS


def test_get_status_errors(database_connection):
    empty = MagicCastle("empty.calculquebec.cloud")
    assert empty.status == ClusterStatusCode.BUILD_ERROR
    missingnodes = MagicCastle("missingnodes.sub.example.com")
    assert missingnodes.status == ClusterStatusCode.BUILD_ERROR


def test_get_status_not_found(database_connection):
    magic_castle1 = MagicCastle("nonexisting.sub.example.com")
    assert magic_castle1.status == ClusterStatusCode.NOT_FOUND
    magic_castle2 = MagicCastle()
    assert magic_castle2.status == ClusterStatusCode.NOT_FOUND


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
    assert magic_castle.owner.id == "bob12.bobby@computecanada.ca"


def test_get_owner_no_owner(database_connection):
    magic_castle = MagicCastle("noowner.calculquebec.cloud")
    assert magic_castle.owner.id == None


def test_dump_configuration_valid(database_connection):
    magic_castle = MagicCastle("valid1.calculquebec.cloud")
    assert magic_castle.dump_configuration() == {
        "cluster_name": "valid1",
        "nb_users": 10,
        "guest_passwd": "password-123",
        "volumes": {
            "nfs": {
                "home": {"size": 100},
                "project": {"size": 50},
                "scratch": {"size": 50},
            }
        },
        "instances": {
            "mgmt": {"type": "p4-6gb", "count": 1, "tags": ["mgmt", "nfs", "puppet"]},
            "login": {
                "type": "p4-6gb",
                "count": 1,
                "tags": ["login", "proxy", "public"],
            },
            "node": {"type": "p2-3gb", "count": 1, "tags": ["node"]},
        },
        "domain": "calculquebec.cloud",
        "hieradata": "",
        "public_keys": ["ssh-rsa FAKE"],
        "image": "CentOS-7-x64-2021-11",
    }
    assert magic_castle.dump_configuration() == {
        "cluster_name": "valid1",
        "nb_users": 10,
        "guest_passwd": "password-123",
        "volumes": {
            "nfs": {
                "home": {"size": 100},
                "project": {"size": 50},
                "scratch": {"size": 50},
            }
        },
        "instances": {
            "mgmt": {"type": "p4-6gb", "count": 1, "tags": ["mgmt", "nfs", "puppet"]},
            "login": {
                "type": "p4-6gb",
                "count": 1,
                "tags": ["login", "proxy", "public"],
            },
            "node": {"type": "p2-3gb", "count": 1, "tags": ["node"]},
        },
        "domain": "calculquebec.cloud",
        "hieradata": "",
        "public_keys": ["ssh-rsa FAKE"],
        "image": "CentOS-7-x64-2021-11",
    }


def test_dump_configuration_empty(database_connection):
    magic_castle = MagicCastle("empty.calculquebec.cloud")
    assert magic_castle.dump_configuration() == dict()


# skip test
@pytest.mark.skip(reason="BROKEN")
def test_dump_configuration_empty_state(database_connection):
    magic_castle = MagicCastle("empty-state.calculquebec.cloud")
    assert magic_castle.dump_configuration() == {
        "cluster_name": "empty-state",
        "nb_users": 34,
        "guest_passwd": "password-123",
        "volumes": {
            "nfs": {
                "home": {"size": 73},
                "scratch": {"size": 1},
                "project": {"size": 1},
            }
        },
        "instances": {
            "mgmt": {"type": "", "count": 0, "tags": ["mgmt", "nfs", "puppet"]},
            "login": {"type": "", "count": 0, "tags": ["login", "proxy", "public"]},
            "node": {"type": "", "count": 0, "tags": ["node"]},
        },
        "domain": "calculquebec.cloud",
        "hieradata": "",
        "public_keys": ["ssh-rsa FAKE"],
        "image": "",
    }


@pytest.mark.skip(reason="BROKEN")
def test_dump_configuration_missing_nodes(database_connection):
    magic_castle = MagicCastle("missingnodes.sub.example.com")
    assert magic_castle.dump_configuration() == {
        "cluster_name": "missingnodes",
        "nb_users": 10,
        "guest_passwd": "password-123",
        "volumes": {
            "nfs": {
                "home": {"size": 100},
                "scratch": {"size": 50},
                "project": {"size": 50},
            }
        },
        "instances": {
            "mgmt": {"type": "p4-6gb", "count": 1, "tags": ["mgmt", "nfs", "puppet"]},
            "login": {
                "type": "p4-6gb",
                "count": 1,
                "tags": ["login", "proxy", "public"],
            },
            "node": {"type": "p2-3gb", "count": 1, "tags": ["node"]},
        },
        "domain": "sub.example.com",
        "hieradata": "",
        "public_keys": ["ssh-rsa FAKE"],
        "image": "CentOS-7-x64-2021-11",
    }
    assert magic_castle.dump_configuration() == {
        "cluster_name": "missingnodes",
        "nb_users": 10,
        "guest_passwd": "password-123",
        "volumes": {
            "nfs": {
                "home": {"size": 100},
                "scratch": {"size": 50},
                "project": {"size": 50},
            }
        },
        "instances": {
            "mgmt": {"type": "", "count": 0, "tags": ["mgmt", "nfs", "puppet"]},
            "login": {"type": "", "count": 0, "tags": ["login", "proxy", "public"]},
            "node": {"type": "", "count": 0, "tags": ["node"]},
        },
        "domain": "sub.example.com",
        "hieradata": "",
        "public_keys": ["ssh-rsa FAKE"],
        "image": "CentOS-7-x64-2021-11",
    }


def test_dump_configuration_busy(database_connection):
    magic_castle = MagicCastle("missingfloatingips.c3.ca")
    assert magic_castle.dump_configuration() == {
        "cluster_name": "missingfloatingips",
        "domain": "c3.ca",
        "image": "CentOS-7-x64-2021-11",
        "nb_users": 17,
        "instances": {
            "mgmt": {"type": "p4-6gb", "count": 1, "tags": ["mgmt", "nfs", "puppet"]},
            "login": {
                "type": "p4-6gb",
                "count": 1,
                "tags": ["login", "proxy", "public"],
            },
            "node": {"type": "p2-3gb", "count": 3, "tags": ["node"]},
        },
        "volumes": {
            "nfs": {
                "home": {"size": 50},
                "scratch": {"size": 1},
                "project": {"size": 1},
            }
        },
        "public_keys": ["ssh-rsa FAKE"],
        "hieradata": "",
        "guest_passwd": "password-123",
    }


def test_dump_configuration_not_found(database_connection):
    magic_castle = MagicCastle()
    with pytest.raises(ClusterNotFoundException):
        magic_castle.dump_configuration()


def test_get_allocated_resources_valid(database_connection):
    """
    Mock context :

    valid1 cluster uses:
    1 + 1 + 1 = 3 instances
    4 + 4 + 2 = 10 vcpus
    6144 + 6144 + 3072 = 15360 ram (15 GiO)
    3 [external volumes] = 3 volumes
    50 + 50 + 100 [external volumes] = 200 GiO of volume storage

    openstack's quotas says there currently remains:
    128 - 28 = 100 instances
    500 - 199 = 301 vcpus
    286,720 - 184,320 = 102,400 ram (100 GiO)
    128 - 100 = 28 volumes
    1000 - 720 = 280 GiO of volume storage

    Therefore, valid1 cluster can use a total of:
    3 instances
    10  vcpus
    15,360 GiB ram
    3 volumes
    200 GiB of volume storage
    """
    magic_castle = MagicCastle("valid1.calculquebec.cloud")
    assert magic_castle.get_allocated_resources() == {
        "pre_allocated_instance_count": 3,
        "pre_allocated_ram": 15360,
        "pre_allocated_cores": 10,
        "pre_allocated_volume_count": 3,
        "pre_allocated_volume_size": 200,
    }


def test_get_allocated_resources_empty(database_connection):
    """
    Mock context :

    empty cluster uses 0 vcpus, 0 ram, 0 volume
    """
    magic_castle = MagicCastle("empty.calculquebec.cloud")
    assert magic_castle.get_allocated_resources() == {
        "pre_allocated_instance_count": 0,
        "pre_allocated_ram": 0,
        "pre_allocated_cores": 0,
        "pre_allocated_volume_count": 0,
        "pre_allocated_volume_size": 0,
    }


def test_get_allocated_resources_missing_nodes(database_connection):
    """
    Mock context :

    missingnodes cluster uses
    0 instance
    0 vcpus
    0 ram
    0 [root disks] + 3 [external volumes] = 3 volumes
    0 + 0 + 0 [root disks]
    + 50 + 50 + 100 [external volumes] = 200 GiO of volume storage
    """
    magic_castle = MagicCastle("missingnodes.sub.example.com")
    assert magic_castle.get_allocated_resources() == {
        "pre_allocated_instance_count": 0,
        "pre_allocated_ram": 0,
        "pre_allocated_cores": 0,
        "pre_allocated_volume_count": 3,
        "pre_allocated_volume_size": 200,
    }


def test_get_allocated_resources_not_found(database_connection):
    """
    Mock context :

    empty cluster uses 0 vcpus, 0 ram, 0 volume
    """
    magic_castle = MagicCastle()
    assert magic_castle.get_allocated_resources() == {
        "pre_allocated_instance_count": 0,
        "pre_allocated_ram": 0,
        "pre_allocated_cores": 0,
        "pre_allocated_volume_count": 0,
        "pre_allocated_volume_size": 0,
    }
