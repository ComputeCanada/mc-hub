import pytest

from copy import deepcopy
from subprocess import CalledProcessError


from ...test_helpers import (
    client,
    app,
    generate_test_clusters,
    mock_clusters_path,
    mock_github_storage_api,
    mock_terraform_cloud_api,
    mock_status_logic,
)  # noqa;
from ...mocks.configuration.config_mock import (
    config_auth_none_mock as config_mock,
)  # noqa;
from ...mocks.github_api_mock import GithubStorageMock
from ...data import CLUSTERS_CONFIG, VALID_CLUSTER_CONFIGURATION


def test_create_magic_castle_plan_valid(app, mocker):
    from mchub.models.magic_castle.magic_castle import MagicCastle
    from mchub.services.terraform_cloud_api import get_terraform_cloud

    create_workspace = mocker.spy(get_terraform_cloud(), "create_workspace")

    cluster = MagicCastle()
    cluster.plan_creation(deepcopy(VALID_CLUSTER_CONFIGURATION))

    create_workspace.assert_called_once_with(
        VALID_CLUSTER_CONFIGURATION["cluster_name"],
        "MOCK_ORG/MOCK_REPO",
        "tfcloud_id",
    )


def test_planned_status_waits_for_local_plan(app):
    from mchub.database import db
    from mchub.models.magic_castle.cluster_status_code import ClusterStatusCode
    from mchub.models.magic_castle.magic_castle import MagicCastle, MagicCastleORM

    orm = db.session.scalar(
        db.select(MagicCastleORM).filter_by(
            hostname="valid1.magic-castle.cloud"
        )
    )
    cluster = MagicCastle(orm)
    cluster.tfcloud_run.run_id = "RUN_WITH_DELAYED_PLAN"
    cluster.tfcloud_run.plan = None
    orm.status = ClusterStatusCode.PLAN_RUNNING
    db.session.commit()

    assert cluster.status == ClusterStatusCode.PLAN_RUNNING

    cluster.tfcloud_run.plan = {"MOCK": "PLAN_LOG"}
    db.session.commit()
    assert cluster.status == ClusterStatusCode.CREATED


def test_create_magic_castle_twice(app):
    from mchub.models.magic_castle.magic_castle import MagicCastle
    from mchub.exceptions.invalid_usage_exception import (
        ClusterExistsException,
    )

    cluster1 = MagicCastle()
    cluster1.plan_creation(deepcopy(VALID_CLUSTER_CONFIGURATION))

    cluster2 = MagicCastle()
    with pytest.raises(ClusterExistsException):
        cluster2.plan_creation(deepcopy(VALID_CLUSTER_CONFIGURATION))


def test_create_magic_castle_init_fail(app, monkeypatch):
    from mchub.models.magic_castle.magic_castle import MagicCastle
    from mchub.exceptions.server_exception import PlanException

    from mchub.services.github_api import _github_storage_instance

    # Define a function that raises the exception you want
    def raise_on_write(*args, **kwargs):
        raise RuntimeError("GitHub write failed")

    # Patch the method on the existing mock instance
    monkeypatch.setattr(_github_storage_instance, "write", raise_on_write)

    cluster = MagicCastle()
    with pytest.raises(
        PlanException, match="Could not write variables.tf on the storage backend."
    ):
        cluster.plan_creation(deepcopy(VALID_CLUSTER_CONFIGURATION))


def test_get_status_valid(app):
    from mchub.models.magic_castle.magic_castle import MagicCastle, MagicCastleORM
    from mchub.models.magic_castle.cluster_status_code import ClusterStatusCode
    from mchub.database import db

    orm = db.session.scalar(
        db.select(MagicCastleORM).filter_by(hostname="created.magic-castle.cloud")
    )
    created = MagicCastle(orm=orm)
    assert created.orm.status == ClusterStatusCode.CREATED

    orm = db.session.scalar(
        db.select(MagicCastleORM).filter_by(hostname="buildplanning.magic-castle.cloud")
    )
    buildplanning = MagicCastle(orm=orm)
    assert buildplanning.orm.status == ClusterStatusCode.PLAN_RUNNING

    orm = db.session.scalar(
        db.select(MagicCastleORM).filter_by(hostname="valid1.magic-castle.cloud")
    )
    valid1 = MagicCastle(orm=orm)
    assert valid1.orm.status == ClusterStatusCode.PROVISIONING_SUCCESS


def test_destroyed_cluster_state_archives_github_repo(app, mocker):
    from mchub.database import db
    from mchub.models.magic_castle.cluster_status_code import ClusterStatusCode
    from mchub.models.magic_castle.magic_castle import MagicCastle, MagicCastleORM
    from mchub.services.github_api import get_github_storage

    orm = db.session.scalar(
        db.select(MagicCastleORM).filter_by(hostname="valid1.magic-castle.cloud")
    )
    cluster = MagicCastle(orm=orm)
    archive_repo = mocker.spy(get_github_storage(), "archive_repo")
    cluster.orm.status = ClusterStatusCode.DESTROY_SUCCESS

    state = cluster.state

    assert state["status"] == ClusterStatusCode.DESTROY_SUCCESS
    assert state["cloud"] == {"name": "project-alice", "id": 1}
    archive_repo.assert_called_once_with("valid1.magic-castle.cloud")


def test_get_status_errors(app):
    from mchub.models.magic_castle.magic_castle import MagicCastle, MagicCastleORM
    from mchub.models.magic_castle.cluster_status_code import ClusterStatusCode
    from mchub.database import db

    orm = db.session.scalar(
        db.select(MagicCastleORM).filter_by(hostname="missingnodes.mc.ca")
    )
    missingnodes = MagicCastle(orm=orm)
    assert missingnodes.orm.status == ClusterStatusCode.BUILD_ERROR


def test_get_status_not_found(app):
    from mchub.models.magic_castle.magic_castle import MagicCastle, MagicCastleORM
    from mchub.models.magic_castle.cluster_status_code import ClusterStatusCode
    from mchub.database import db

    orm = db.session.scalar(
        db.select(MagicCastleORM).filter_by(hostname="nonexisting.mc.ca")
    )
    magic_castle1 = MagicCastle(orm=orm)
    assert magic_castle1.orm.status == ClusterStatusCode.NOT_FOUND
    magic_castle2 = MagicCastle()
    assert magic_castle2.orm.status == ClusterStatusCode.NOT_FOUND


def test_config_valid(app):
    from mchub.models.magic_castle.magic_castle import MagicCastle, MagicCastleORM
    from mchub.database import db

    hostname = "valid1.magic-castle.cloud"
    orm = db.session.scalar(db.select(MagicCastleORM).filter_by(hostname=hostname))
    magic_castle = MagicCastle(orm=orm)
    assert magic_castle.config == CLUSTERS_CONFIG[hostname]


def test_config_busy(app):
    from mchub.models.magic_castle.magic_castle import MagicCastle, MagicCastleORM
    from mchub.database import db

    hostname = "missingfloatingips.mc.ca"
    orm = db.session.scalar(db.select(MagicCastleORM).filter_by(hostname=hostname))
    magic_castle = MagicCastle(orm=orm)
    assert magic_castle.config == CLUSTERS_CONFIG[hostname]


def test_config_empty(app):
    from mchub.models.magic_castle.magic_castle import MagicCastle

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
    from mchub.models.magic_castle.magic_castle import MagicCastle, MagicCastleORM
    from mchub.database import db

    orm = db.session.scalar(
        db.select(MagicCastleORM).filter_by(hostname="valid1.magic-castle.cloud")
    )
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
    from mchub.models.magic_castle.magic_castle import MagicCastle, MagicCastleORM
    from mchub.database import db

    orm = db.session.scalar(
        db.select(MagicCastleORM).filter_by(hostname="missingnodes.mc.ca")
    )
    magic_castle = MagicCastle(orm=orm)
    assert magic_castle.allocated_resources == {
        "pre_allocated_instance_count": 0,
        "pre_allocated_ram": 0,
        "pre_allocated_cores": 0,
        "pre_allocated_volume_count": 3,
        "pre_allocated_volume_size": 200,
    }


@pytest.mark.usefixtures("mock_status_logic")
def test_allocated_resources_not_found(app):
    """
    Mock context :

    empty cluster uses 0 vcpus, 0 ram, 0 volume
    """
    from mchub.models.magic_castle.magic_castle import MagicCastle

    magic_castle = MagicCastle()
    assert magic_castle.allocated_resources == {
        "pre_allocated_instance_count": 0,
        "pre_allocated_ram": 0,
        "pre_allocated_cores": 0,
        "pre_allocated_volume_count": 0,
        "pre_allocated_volume_size": 0,
    }
