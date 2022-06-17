import pytest

from copy import deepcopy
from subprocess import CalledProcessError

from mchub.models.magic_castle.magic_castle import MagicCastle, MagicCastleORM
from mchub.models.magic_castle.cluster_status_code import ClusterStatusCode
from mchub.models.magic_castle.plan_type import PlanType
from mchub.exceptions.invalid_usage_exception import (
    ClusterNotFoundException,
    ClusterExistsException,
    PlanNotCreatedException,
)
from mchub.exceptions.server_exception import PlanException

from ...test_helpers import *  # noqa;
from ...mocks.configuration.config_mock import config_auth_none_mock  # noqa;
from ...data import CLUSTERS_CONFIG, VALID_CLUSTER_CONFIGURATION


@pytest.mark.usefixtures("fake_successful_subprocess_run")
def test_create_magic_castle_plan_valid(app):
    cluster = MagicCastle()
    cluster.plan_creation(deepcopy(VALID_CLUSTER_CONFIGURATION))


@pytest.mark.usefixtures("fake_successful_subprocess_run")
def test_create_magic_castle_twice(app):
    cluster1 = MagicCastle()
    cluster1.plan_creation(deepcopy(VALID_CLUSTER_CONFIGURATION))

    cluster2 = MagicCastle()
    with pytest.raises(ClusterExistsException):
        cluster2.plan_creation(deepcopy(VALID_CLUSTER_CONFIGURATION))


def test_apply_before_planning(app):
    cluster = MagicCastle()
    with pytest.raises(PlanNotCreatedException):
        cluster.apply()


def test_create_magic_castle_init_fail(app, monkeypatch):
    def fake_run(process_args, *args, **kwargs):
        if process_args == ["terraform", "init", "-no-color", "-input=false"]:
            raise CalledProcessError(1, "terraform init")

    monkeypatch.setattr("mchub.models.magic_castle.magic_castle.run", fake_run)
    cluster = MagicCastle()
    with pytest.raises(PlanException, match="Could not initialize Terraform modules."):
        cluster.plan_creation(deepcopy(VALID_CLUSTER_CONFIGURATION))


def test_create_magic_castle_plan_fail(app, monkeypatch):
    def fake_run(process_args, *args, **kwargs):
        if process_args[:2] == [
            "terraform",
            "plan",
        ]:
            raise CalledProcessError(1, "terraform plan")

    monkeypatch.setattr("mchub.models.magic_castle.magic_castle.run", fake_run)
    cluster = MagicCastle()
    with pytest.raises(
        PlanException, match="An error occurred while planning changes."
    ):
        cluster.plan_creation(deepcopy(VALID_CLUSTER_CONFIGURATION))


def test_create_magic_castle_plan_export_fail(app, monkeypatch):
    def fake_run(process_args, *args, **kwargs):
        if process_args[:4] == [
            "terraform",
            "show",
            "-no-color",
            "-json",
        ]:
            raise CalledProcessError(1, "terraform show")

    monkeypatch.setattr("mchub.models.magic_castle.magic_castle.run", fake_run)
    cluster = MagicCastle()
    with pytest.raises(
        PlanException, match="An error occurred while exporting planned changes."
    ):
        cluster.plan_creation(deepcopy(VALID_CLUSTER_CONFIGURATION))


def test_get_status_valid(app):
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


def test_get_status_errors(app):

    orm = MagicCastleORM.query.filter_by(hostname="missingnodes.c3.ca").first()
    missingnodes = MagicCastle(orm=orm)
    assert missingnodes.status == ClusterStatusCode.BUILD_ERROR


def test_get_status_not_found(app):
    orm = MagicCastleORM.query.filter_by(hostname="nonexisting.c3.ca").first()
    magic_castle1 = MagicCastle(orm=orm)
    assert magic_castle1.status == ClusterStatusCode.NOT_FOUND
    magic_castle2 = MagicCastle()
    assert magic_castle2.status == ClusterStatusCode.NOT_FOUND


def test_get_plan_type_build(app):
    orm = MagicCastleORM.query.filter_by(
        hostname="buildplanning.calculquebec.cloud"
    ).first()
    build_planning = MagicCastle(orm=orm)
    assert build_planning.plan_type == PlanType.BUILD
    orm = MagicCastleORM.query.filter_by(hostname="created.calculquebec.cloud").first()
    created = MagicCastle(orm=orm)
    assert created.plan_type == PlanType.BUILD


def test_get_plan_type_destroy(app):
    orm = MagicCastleORM.query.filter_by(hostname="valid1.calculquebec.cloud").first()
    magic_castle = MagicCastle(orm=orm)
    assert magic_castle.plan_type == PlanType.DESTROY


def test_get_plan_type_none(app):
    orm = MagicCastleORM.query.filter_by(hostname="missingfloatingips.c3.ca").first()
    magic_castle = MagicCastle(orm=orm)
    assert magic_castle.plan_type == PlanType.NONE


def test_config_valid(app):
    hostname = "valid1.calculquebec.cloud"
    orm = MagicCastleORM.query.filter_by(hostname=hostname).first()
    magic_castle = MagicCastle(orm=orm)
    assert magic_castle.config == CLUSTERS_CONFIG[hostname]


def test_config_busy(app):
    hostname = "missingfloatingips.c3.ca"
    orm = MagicCastleORM.query.filter_by(hostname=hostname).first()
    magic_castle = MagicCastle(orm=orm)
    assert magic_castle.config == CLUSTERS_CONFIG[hostname]


def test_config_empty(app):
    magic_castle = MagicCastle()
    assert magic_castle.config == {}


def test_allocated_resources_valid(app):
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
    orm = MagicCastleORM.query.filter_by(hostname="valid1.calculquebec.cloud").first()
    magic_castle = MagicCastle(orm=orm)
    assert magic_castle.allocated_resources == {
        "pre_allocated_instance_count": 3,
        "pre_allocated_ram": 15360,
        "pre_allocated_cores": 10,
        "pre_allocated_volume_count": 3,
        "pre_allocated_volume_size": 200,
    }


def test_allocated_resources_missing_nodes(app):
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
    orm = MagicCastleORM.query.filter_by(hostname="missingnodes.c3.ca").first()
    magic_castle = MagicCastle(orm=orm)
    assert magic_castle.allocated_resources == {
        "pre_allocated_instance_count": 0,
        "pre_allocated_ram": 0,
        "pre_allocated_cores": 0,
        "pre_allocated_volume_count": 3,
        "pre_allocated_volume_size": 200,
    }


def test_allocated_resources_not_found(app):
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
