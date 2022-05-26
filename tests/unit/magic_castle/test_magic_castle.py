import pytest

from copy import deepcopy
from subprocess import CalledProcessError

from mchub.configuration.cloud import DEFAULT_CLOUD
from mchub.models.magic_castle.magic_castle import MagicCastle, MagicCastleORM
from mchub.models.magic_castle.cluster_status_code import ClusterStatusCode
from mchub.models.magic_castle.plan_type import PlanType
from mchub.exceptions.invalid_usage_exception import ClusterNotFoundException
from mchub.exceptions.server_exception import PlanException

from ...test_helpers import *  # noqa;
from ...mocks.configuration.config_mock import config_auth_none_mock  # noqa;


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
def test_create_magic_castle_plan_valid(client):
    client.get("/api/users/me")
    cluster = MagicCastle()
    cluster.plan_creation(deepcopy(VALID_CLUSTER_CONFIGURATION))


def test_create_magic_castle_init_fail(client, monkeypatch):
    def fake_run(process_args, *args, **kwargs):
        if process_args == ["terraform", "init", "-no-color", "-input=false"]:
            raise CalledProcessError(1, "terraform init")

    client.get("/api/users/me")
    monkeypatch.setattr("mchub.models.magic_castle.magic_castle.run", fake_run)
    cluster = MagicCastle()
    with pytest.raises(
        PlanException, match="An error occurred while initializing Terraform."
    ):
        cluster.plan_creation(deepcopy(VALID_CLUSTER_CONFIGURATION))


def test_create_magic_castle_plan_fail(client, monkeypatch):
    def fake_run(process_args, *args, **kwargs):
        if process_args[:2] == [
            "terraform",
            "plan",
        ]:
            raise CalledProcessError(1, "terraform plan")

    client.get("/api/users/me")
    monkeypatch.setattr("mchub.models.magic_castle.magic_castle.run", fake_run)
    cluster = MagicCastle()
    with pytest.raises(
        PlanException, match="An error occurred while planning changes."
    ):
        cluster.plan_creation(deepcopy(VALID_CLUSTER_CONFIGURATION))


def test_create_magic_castle_plan_export_fail(client, monkeypatch):
    def fake_run(process_args, *args, **kwargs):
        if process_args[:4] == [
            "terraform",
            "show",
            "-no-color",
            "-json",
        ]:
            raise CalledProcessError(1, "terraform show")

    client.get("/api/users/me")
    monkeypatch.setattr("mchub.models.magic_castle.magic_castle.run", fake_run)
    cluster = MagicCastle()
    with pytest.raises(
        PlanException, match="An error occurred while exporting planned changes."
    ):
        cluster.plan_creation(deepcopy(VALID_CLUSTER_CONFIGURATION))


def test_get_status_valid(client):
    client.get("/api/users/me")
    orm = MagicCastleORM.query.filter_by(hostname="created.calculquebec.cloud").first()
    created = MagicCastle(orm=orm)
    assert created.status == ClusterStatusCode.CREATED

    orm = MagicCastleORM.query.filter_by(
        hostname="buildplanning.calculquebec.cloud"
    ).first()
    buildplanning = MagicCastle(orm=orm)
    assert buildplanning.status == ClusterStatusCode.PLAN_RUNNING

    orm = MagicCastleORM.query.filter_by(hostname="valid1.calculquebec.cloud").first()
    valid1 = MagicCastle(orm=orm)
    assert valid1.status == ClusterStatusCode.PROVISIONING_SUCCESS


def test_get_status_errors(client):
    client.get("/api/users/me")
    orm = MagicCastleORM.query.filter_by(hostname="empty.calculquebec.cloud").first()
    empty = MagicCastle(orm=orm)
    assert empty.status == ClusterStatusCode.BUILD_ERROR

    orm = MagicCastleORM.query.filter_by(hostname="missingnodes.c3.ca").first()
    missingnodes = MagicCastle(orm=orm)
    assert missingnodes.status == ClusterStatusCode.BUILD_ERROR


def test_get_status_not_found(client):
    client.get("/api/users/me")
    orm = MagicCastleORM.query.filter_by(hostname="nonexisting.c3.ca").first()
    magic_castle1 = MagicCastle(orm=orm)
    assert magic_castle1.status == ClusterStatusCode.NOT_FOUND
    magic_castle2 = MagicCastle()
    assert magic_castle2.status == ClusterStatusCode.NOT_FOUND


def test_get_plan_type_build(client):
    client.get("/api/users/me")
    orm = MagicCastleORM.query.filter_by(
        hostname="buildplanning.calculquebec.cloud"
    ).first()
    build_planning = MagicCastle(orm=orm)
    assert build_planning.plan_type == PlanType.BUILD
    orm = MagicCastleORM.query.filter_by(hostname="created.calculquebec.cloud").first()
    created = MagicCastle(orm=orm)
    assert created.plan_type == PlanType.BUILD


def test_get_plan_type_destroy(client):
    client.get("/api/users/me")
    orm = MagicCastleORM.query.filter_by(hostname="valid1.calculquebec.cloud").first()
    magic_castle = MagicCastle(orm=orm)
    assert magic_castle.plan_type == PlanType.DESTROY


def test_get_plan_type_none(client):
    client.get("/api/users/me")
    orm = MagicCastleORM.query.filter_by(hostname="missingfloatingips.c3.ca").first()
    magic_castle = MagicCastle(orm=orm)
    assert magic_castle.plan_type == PlanType.NONE


def test_get_owner_valid(client):
    client.get("/api/users/me")
    orm = MagicCastleORM.query.filter_by(hostname="missingfloatingips.c3.ca").first()
    magic_castle = MagicCastle(orm=orm)
    assert magic_castle.owner == "bob12.bobby@computecanada.ca"


def test_get_owner_no_owner(client):
    client.get("/api/users/me")
    orm = MagicCastleORM.query.filter_by(hostname="noowner.calculquebec.cloud").first()
    magic_castle = MagicCastle(orm=orm)
    assert magic_castle.owner == None


def test_config_valid(client):
    client.get("/api/users/me")
    orm = MagicCastleORM.query.filter_by(hostname="valid1.calculquebec.cloud").first()
    magic_castle = MagicCastle(orm=orm)
    assert magic_castle.config == {
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
    assert magic_castle.config == {
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


def test_config_empty(client):
    client.get("/api/users/me")
    orm = MagicCastleORM.query.filter_by(hostname="empty.calculquebec.cloud").first()
    magic_castle = MagicCastle(orm=orm)
    assert magic_castle.config == dict()


def test_config_busy(client):
    client.get("/api/users/me")
    orm = MagicCastleORM.query.filter_by(hostname="missingfloatingips.c3.ca").first()
    magic_castle = MagicCastle(orm=orm)
    assert magic_castle.config == {
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


def test_config_empty(client):
    magic_castle = MagicCastle()
    assert magic_castle.config == {}


def test_allocated_resources_valid(client):
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
    client.get("/api/users/me")
    orm = MagicCastleORM.query.filter_by(hostname="valid1.calculquebec.cloud").first()
    magic_castle = MagicCastle(orm=orm)
    assert magic_castle.allocated_resources == {
        "pre_allocated_instance_count": 3,
        "pre_allocated_ram": 15360,
        "pre_allocated_cores": 10,
        "pre_allocated_volume_count": 3,
        "pre_allocated_volume_size": 200,
    }


def test_allocated_resources_empty(client):
    """
    Mock context :

    empty cluster uses 0 vcpus, 0 ram, 0 volume
    """
    client.get("/api/users/me")
    orm = MagicCastleORM.query.filter_by(hostname="empty.calculquebec.cloud").first()
    magic_castle = MagicCastle(orm=orm)
    assert magic_castle.allocated_resources == {
        "pre_allocated_instance_count": 0,
        "pre_allocated_ram": 0,
        "pre_allocated_cores": 0,
        "pre_allocated_volume_count": 0,
        "pre_allocated_volume_size": 0,
    }


def test_allocated_resources_missing_nodes(client):
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
    client.get("/api/users/me")
    orm = MagicCastleORM.query.filter_by(hostname="missingnodes.c3.ca").first()
    magic_castle = MagicCastle(orm=orm)
    assert magic_castle.allocated_resources == {
        "pre_allocated_instance_count": 0,
        "pre_allocated_ram": 0,
        "pre_allocated_cores": 0,
        "pre_allocated_volume_count": 3,
        "pre_allocated_volume_size": 200,
    }


def test_allocated_resources_not_found(client):
    """
    Mock context :

    empty cluster uses 0 vcpus, 0 ram, 0 volume
    """
    magic_castle = MagicCastle()
    assert magic_castle.allocated_resources == {
        "pre_allocated_instance_count": 0,
        "pre_allocated_ram": 0,
        "pre_allocated_cores": 0,
        "pre_allocated_volume_count": 0,
        "pre_allocated_volume_size": 0,
    }
