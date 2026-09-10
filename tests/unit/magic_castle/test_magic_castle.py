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
    from mchub.services.github_api import get_github_storage

    create_workspace = mocker.spy(get_terraform_cloud(), "create_workspace")
    write_variables = mocker.spy(get_github_storage(), "write")

    cluster = MagicCastle()
    cluster.plan_creation(deepcopy(VALID_CLUSTER_CONFIGURATION))

    create_workspace.assert_called_once_with(
        VALID_CLUSTER_CONFIGURATION["cluster_name"],
        "MOCK_ORG/MOCK_REPO",
        "tfcloud_id",
    )
    assert write_variables.call_args.args[0]["mc_version"] == "14.1.2"
    assert cluster.tf_state is None
    assert cluster.state["undeployed"] is True


@pytest.mark.parametrize("has_remote_state", [False, True])
def test_legacy_initial_plan_uses_verified_deployment_state(app, mocker, has_remote_state):
    from mchub.models.magic_castle.magic_castle import MagicCastle
    from mchub.services.terraform_cloud_api import get_terraform_cloud

    cluster = MagicCastle()
    cluster.plan_creation(deepcopy(VALID_CLUSTER_CONFIGURATION))
    cluster.orm.undeployed = False
    original_run = cluster.tfcloud_run.run_id
    inspect_state = mocker.patch.object(
        get_terraform_cloud(), "workspace_has_state", return_value=has_remote_state
    )

    state = cluster.state

    assert state["undeployed"] is not has_remote_state
    assert cluster.tfcloud_run.run_id == original_run
    assert cluster.plan is not None
    inspect_state.assert_called_once_with(cluster.tfcloud_workspace)


@pytest.mark.parametrize("zone", ["ca-central-1a", "ca-central-1b", None])
def test_undeployed_aws_zone_survives_save_and_reload(app, zone):
    from mchub.database import db
    from mchub.models.cloud.project import Project, Provider
    from mchub.models.magic_castle.magic_castle import MagicCastle, MagicCastleORM
    from mchub.models.magic_castle.cluster_status_code import ClusterStatusCode

    project = db.session.get(Project, VALID_CLUSTER_CONFIGURATION["cloud"]["id"])
    project.provider = Provider.AWS
    cluster = MagicCastle()
    cluster.set_configuration({**deepcopy(VALID_CLUSTER_CONFIGURATION), "availability_zone": "ca-central-1a"})
    cluster.orm.undeployed = True
    cluster.orm.status = ClusterStatusCode.NOT_DEPLOYED
    db.session.add(cluster.orm)
    db.session.commit()
    hostname = cluster.hostname

    cluster.plan_modification({**cluster.state, "availability_zone": zone})
    db.session.remove()
    reloaded = MagicCastle(db.session.scalar(db.select(MagicCastleORM).filter_by(hostname=hostname)))
    assert reloaded.state["availability_zone"] == zone


def test_initial_apply_leaves_undeployed_lifecycle(app):
    from mchub.models.magic_castle.magic_castle import MagicCastle

    cluster = MagicCastle()
    cluster.plan_creation(deepcopy(VALID_CLUSTER_CONFIGURATION))
    cluster.apply()

    assert cluster.orm.undeployed is False
    assert cluster.orm.deployment_started_at is not None


def test_create_magic_castle_rejects_unvetted_version(app):
    from mchub.exceptions.invalid_usage_exception import InvalidUsageException
    from mchub.models.magic_castle.magic_castle import MagicCastle

    configuration = deepcopy(VALID_CLUSTER_CONFIGURATION)
    configuration["mc_version"] = "unvetted"

    with pytest.raises(InvalidUsageException, match="Invalid Magic Castle version"):
        MagicCastle().plan_creation(configuration)


def test_creation_steps_are_committed_before_external_operations(app, mocker):
    from mchub.database import db
    from mchub.models.magic_castle.magic_castle import MagicCastle, MagicCastleORM
    from mchub.services.github_api import get_github_storage
    from mchub.services.terraform_cloud_api import get_terraform_cloud

    cluster = MagicCastle()
    observed_steps = []

    def observe(service, method):
        original = getattr(service, method)

        def call(*args, **kwargs):
            # A separate connection models a concurrent status request.
            with db.engine.connect() as connection:
                step = connection.scalar(
                    db.select(MagicCastleORM.creation_step).where(
                        MagicCastleORM.hostname == cluster.hostname
                    )
                )
            observed_steps.append(step)
            return original(*args, **kwargs)

        mocker.patch.object(service, method, autospec=True, side_effect=call)

    observe(get_github_storage(), "create_repo")
    observe(get_terraform_cloud(), "create_workspace")
    observe(get_github_storage(), "write")
    observe(MagicCastle, "create_plan")

    cluster.plan_creation(deepcopy(VALID_CLUSTER_CONFIGURATION))

    assert observed_steps == [
        "github_repository", "terraform_workspace", "variable_file", "resource_plan"
    ]


def test_progress_api_reports_creation_step(app):
    from types import SimpleNamespace
    from mchub.database import db
    from mchub.models.magic_castle.magic_castle import MagicCastleORM
    from mchub.resources.progress_api import ProgressAPI

    orm = db.session.scalar(
        db.select(MagicCastleORM).filter_by(hostname="buildplanning.magic-castle.cloud")
    )
    orm.creation_step = "terraform_workspace"
    db.session.commit()

    result = ProgressAPI().get(SimpleNamespace(projects=[orm.project]), orm.hostname)

    assert result["creation_step"] == "terraform_workspace"


def test_deployed_magic_castle_version_cannot_be_modified(app):
    from mchub.database import db
    from mchub.exceptions.invalid_usage_exception import InvalidUsageException
    from mchub.models.magic_castle.magic_castle import MagicCastle, MagicCastleORM
    from mchub.models.magic_castle.magic_castle_configuration import (
        MagicCastleConfiguration,
    )

    orm = db.session.scalar(
        db.select(MagicCastleORM).filter_by(hostname="valid1.magic-castle.cloud")
    )
    configuration = dict(orm.config)
    configuration["mc_version"] = "14.1.2"
    orm.config = MagicCastleConfiguration("openstack", configuration)

    with pytest.raises(
        InvalidUsageException, match="cannot be changed while the cluster is deployed"
    ):
        MagicCastle(orm).plan_modification({"mc_version": "14.0.0"})


def test_undeployed_magic_castle_rejects_unvetted_version(app):
    from mchub.exceptions.invalid_usage_exception import InvalidUsageException
    from mchub.models.magic_castle.magic_castle import MagicCastle

    cluster = MagicCastle()
    cluster.plan_creation(deepcopy(VALID_CLUSTER_CONFIGURATION))
    original_run_id = cluster.tfcloud_run.run_id

    with pytest.raises(InvalidUsageException, match="Invalid Magic Castle version"):
        cluster.plan_modification({"mc_version": "unvetted"})

    assert cluster.config["mc_version"] == "14.1.2"
    assert cluster.tfcloud_run.run_id == original_run_id


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


def test_successful_provisioning_is_not_reclassified_when_a_service_stops(
    app, mocker
):
    from mchub.database import db
    from mchub.models.magic_castle.cluster_status_code import ClusterStatusCode
    from mchub.models.magic_castle.magic_castle import MagicCastle, MagicCastleORM
    from mchub.models.magic_castle.terraform_cloud_status import TFCloudStatusCode
    from mchub.models.puppet.provisioning_manager import ProvisioningManager

    orm = db.session.scalar(
        db.select(MagicCastleORM).filter_by(hostname="valid1.magic-castle.cloud")
    )
    orm.tfcloud_run.run_id = "completed-run"
    mocker.patch(
        "mchub.models.magic_castle.magic_castle.get_tf_status_cache",
        return_value=(TFCloudStatusCode.APPLIED, False),
    )
    mocker.patch.object(
        ProvisioningManager,
        "check_services",
        return_value={
            "jupyterhub": {
                "label": "JupyterHub",
                "url": "https://jupyter.valid1.magic-castle.cloud",
                "status": "unavailable",
            },
            "freeipa": {
                "label": "FreeIPA",
                "url": "https://ipa.valid1.magic-castle.cloud",
                "status": "healthy",
            },
            "mokey": {
                "label": "Mokey",
                "url": "https://mokey.valid1.magic-castle.cloud",
                "status": "healthy",
            },
        },
    )

    cluster = MagicCastle(orm=orm)

    assert cluster.status == ClusterStatusCode.PROVISIONING_SUCCESS
    assert cluster.health == "degraded"
    assert cluster.service_statuses["jupyterhub"]["status"] == "unavailable"


def test_teardown_retains_cluster_and_integrations(app, mocker):
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

    assert state["status"] == ClusterStatusCode.NOT_DEPLOYED
    assert cluster.status == ClusterStatusCode.NOT_DEPLOYED
    assert cluster.tf_state is None
    assert cluster.freeipa_passwd is None
    assert state["undeployed"] is True
    assert db.session.get(MagicCastleORM, orm.id) is orm
    assert state["cloud"] == {"name": "project-alice", "id": 1}
    archive_repo.assert_not_called()


def test_destroy_cluster_without_terraform_state_skips_destroy_plan(app, mocker):
    from mchub.database import db
    from mchub.models.magic_castle.magic_castle import MagicCastle, MagicCastleORM
    from mchub.services.github_api import get_github_storage
    from mchub.services.terraform_cloud_api import get_terraform_cloud

    hostname = "created.magic-castle.cloud"
    orm = db.session.scalar(db.select(MagicCastleORM).filter_by(hostname=hostname))
    orm.tfcloud_workspace = "ws-without-state"
    db.session.commit()

    terraform = get_terraform_cloud()
    has_state = mocker.patch.object(terraform, "workspace_has_state", return_value=False)
    destroy_plan = mocker.spy(terraform, "destroy_plan")
    add_tag = mocker.spy(terraform, "add_workspace_tag")
    archive_repo = mocker.spy(get_github_storage(), "archive_repo")

    MagicCastle(orm).plan_destruction()

    has_state.assert_called_once_with("ws-without-state")
    destroy_plan.assert_not_called()
    add_tag.assert_not_called()
    archive_repo.assert_not_called()
    assert db.session.scalar(
        db.select(MagicCastleORM).filter_by(hostname=hostname)
    ) is orm
    assert orm.undeployed


def test_destroy_cluster_with_terraform_state_creates_destroy_plan(app, mocker):
    from mchub.database import db
    from mchub.models.magic_castle.magic_castle import MagicCastle, MagicCastleORM
    from mchub.services.terraform_cloud_api import get_terraform_cloud

    orm = db.session.scalar(
        db.select(MagicCastleORM).filter_by(hostname="created.magic-castle.cloud")
    )
    orm.tfcloud_workspace = "ws-with-state"
    db.session.commit()

    terraform = get_terraform_cloud()
    has_state = mocker.patch.object(terraform, "workspace_has_state", return_value=True)
    destroy_plan = mocker.spy(terraform, "destroy_plan")

    MagicCastle(orm).plan_destruction()

    has_state.assert_called_once_with("ws-with-state")
    destroy_plan.assert_called_once_with("ws-with-state")


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


@pytest.mark.parametrize("initial_plan", [False, True])
def test_undeployed_configuration_saves_without_run_and_rebuild_reuses_integrations(app, mocker, initial_plan):
    from mchub.database import db
    from mchub.models.magic_castle.magic_castle import MagicCastle, MagicCastleORM
    from mchub.models.magic_castle.cluster_status_code import ClusterStatusCode
    from mchub.services.github_api import get_github_storage
    from mchub.services.terraform_cloud_api import get_terraform_cloud

    orm = db.session.scalar(db.select(MagicCastleORM).filter_by(hostname="valid1.magic-castle.cloud"))
    cluster = MagicCastle(orm)
    orm.tfcloud_workspace = "existing-workspace"
    if initial_plan:
        cluster = MagicCastle()
        cluster.plan_creation(deepcopy(VALID_CLUSTER_CONFIGURATION))
        orm = cluster.orm
        orm.tfcloud_workspace = "existing-workspace"
    else:
        cluster.complete_teardown()
    config = deepcopy(cluster.state)
    config["expiration_date"] = None
    config["mc_version"] = "14.0.0"
    write = mocker.spy(get_github_storage(), "write")
    create_repo = mocker.spy(get_github_storage(), "create_repo")
    create_workspace = mocker.spy(get_terraform_cloud(), "create_workspace")
    cluster.plan_modification(config)
    write.assert_not_called()
    assert cluster.status == ClusterStatusCode.NOT_DEPLOYED
    assert cluster.config["mc_version"] == "14.0.0"
    assert cluster.plan is None
    assert cluster.tfcloud_run.run_id is None

    cluster.plan_rebuild()
    write.assert_called_once()
    assert write.call_args.args[0]["mc_version"] == "14.0.0"
    create_repo.assert_not_called()
    create_workspace.assert_not_called()
    assert orm.tfcloud_workspace == "existing-workspace"
    assert cluster.status == ClusterStatusCode.CREATED


def test_failed_rebuild_after_save_cannot_restore_previous_plan(app, mocker):
    from mchub.database import db
    from mchub.exceptions.invalid_usage_exception import PlanNotCreatedException
    from mchub.models.magic_castle.magic_castle import MagicCastle, MagicCastleORM
    from mchub.models.magic_castle.cluster_status_code import ClusterStatusCode
    from mchub.models.magic_castle.terraform_cloud_status import TFCloudStatusCode
    from mchub.services.github_api import get_github_storage

    orm = db.session.scalar(db.select(MagicCastleORM).filter_by(hostname="valid1.magic-castle.cloud"))
    cluster = MagicCastle(orm)
    cluster.complete_teardown()
    orm.tfcloud_workspace = "existing-workspace"
    orm.expiration_date = None
    cluster.plan_rebuild()
    assert cluster.plan is not None

    config = deepcopy(cluster.state)
    config["nb_users"] += 1
    cluster.plan_modification(config)

    # Match the background worker's claim and error handling when GitHub fails
    # before create_plan can replace the previous run.
    orm.status = ClusterStatusCode.BACKGROUND_TASK_RUNNING
    db.session.commit()
    mocker.patch.object(get_github_storage(), "write", side_effect=RuntimeError("GitHub unavailable"))
    with pytest.raises(RuntimeError, match="GitHub unavailable"):
        cluster.plan_rebuild()
    db.session.rollback()
    orm.status = ClusterStatusCode.PLAN_ERROR
    db.session.commit()

    remote_status = mocker.patch(
        "mchub.models.magic_castle.magic_castle.get_tf_status_cache",
        return_value=(TFCloudStatusCode.PLANNED, False),
    )
    assert cluster.status == ClusterStatusCode.PLAN_ERROR
    remote_status.assert_not_called()
    assert cluster.tfcloud_run.run_id is None
    assert cluster.plan is None
    assert cluster.config["nb_users"] == config["nb_users"]
    with pytest.raises(PlanNotCreatedException):
        cluster.apply()


def test_rebuild_rejects_past_expiration(app):
    from mchub.database import db
    from mchub.models.magic_castle.magic_castle import MagicCastle, MagicCastleORM
    from mchub.exceptions.invalid_usage_exception import InvalidUsageException

    orm = db.session.scalar(db.select(MagicCastleORM).filter_by(hostname="valid1.magic-castle.cloud"))
    cluster = MagicCastle(orm)
    cluster.complete_teardown()
    orm.tfcloud_workspace = "existing-workspace"
    orm.expiration_date = "2020-01-01"
    with pytest.raises(InvalidUsageException, match="future expiration"):
        cluster.plan_rebuild()


def test_destroy_checks_remote_resources_and_keeps_record_on_failure(app, mocker):
    from mchub.database import db
    from mchub.models.magic_castle.magic_castle import MagicCastle, MagicCastleORM
    from mchub.services.terraform_cloud_api import get_terraform_cloud
    from mchub.services.github_api import get_github_storage
    from mchub.exceptions.invalid_usage_exception import InvalidUsageException

    orm = db.session.scalar(db.select(MagicCastleORM).filter_by(hostname="valid1.magic-castle.cloud"))
    cluster = MagicCastle(orm)
    cluster.complete_teardown()
    orm.tfcloud_workspace = "existing-workspace"
    tf = get_terraform_cloud()
    order = mocker.Mock()
    discard = mocker.spy(tf, "discard_workspace_plans")
    lock = mocker.patch.object(tf, "lock_workspace", create=True)
    unlock = mocker.patch.object(tf, "unlock_workspace", create=True)
    verify = mocker.patch.object(tf, "verify_workspace_empty", create=True, side_effect=InvalidUsageException("resources remain"))
    archive = mocker.spy(get_github_storage(), "archive_repo")
    for name, operation in [("discard", discard), ("lock", lock), ("verify", verify), ("archive", archive)]:
        order.attach_mock(operation, name)
    with pytest.raises(InvalidUsageException):
        cluster.destroy_empty_cluster()
    assert db.session.get(MagicCastleORM, orm.id) is orm
    archive.assert_not_called()
    lock.assert_called_once_with("existing-workspace")
    unlock.assert_called_once_with("existing-workspace")
    verify.side_effect = None
    order.mock_calls = []
    cluster.destroy_empty_cluster()
    assert [call[0] for call in order.mock_calls] == ["discard", "lock", "verify", "archive"]
    archive.assert_called_once_with("valid1.magic-castle.cloud")
    assert db.session.scalar(db.select(MagicCastleORM).filter_by(hostname="valid1.magic-castle.cloud")) is None


def test_rebuild_apply_starts_new_provisioning_timeout(app, mocker):
    import datetime
    from mchub.database import db
    from mchub.models.magic_castle.magic_castle import MagicCastle, MagicCastleORM
    from mchub.models.magic_castle.cluster_status_code import ClusterStatusCode
    from mchub.models.magic_castle.terraform_cloud_status import TFCloudStatusCode
    from mchub.services.terraform_cloud_api import get_terraform_cloud

    orm = db.session.scalar(db.select(MagicCastleORM).filter_by(hostname="valid1.magic-castle.cloud"))
    cluster = MagicCastle(orm)
    original_created = orm.created
    cluster.complete_teardown()
    orm.tfcloud_workspace = "existing-workspace"
    orm.expiration_date = None
    cluster.plan_rebuild()
    cluster.apply()
    assert not orm.undeployed
    assert orm.created == original_created
    assert (datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) - orm.deployment_started_at).total_seconds() < 5
    mocker.patch("mchub.models.magic_castle.magic_castle.get_tf_status_cache", return_value=(TFCloudStatusCode.APPLIED, False))
    mocker.patch.object(MagicCastle, "services_are_online", new_callable=mocker.PropertyMock, return_value=False)
    assert cluster.status == ClusterStatusCode.PROVISIONING_RUNNING


def test_destroy_retains_initial_cluster_if_discard_fails(app, mocker):
    from mchub.database import db
    from mchub.models.magic_castle.magic_castle import MagicCastle, MagicCastleORM
    from mchub.services.terraform_cloud_api import get_terraform_cloud
    from mchub.services.github_api import get_github_storage
    from mchub.exceptions.server_exception import TerraformCloudException

    cluster = MagicCastle()
    cluster.plan_creation(deepcopy(VALID_CLUSTER_CONFIGURATION))
    tf = get_terraform_cloud()
    mocker.patch.object(tf, "discard_workspace_plans", side_effect=TerraformCloudException("discard failed"))
    lock = mocker.patch.object(tf, "lock_workspace", create=True)
    archive = mocker.spy(get_github_storage(), "archive_repo")
    with pytest.raises(TerraformCloudException, match="discard failed"):
        cluster.destroy_empty_cluster()
    assert db.session.get(MagicCastleORM, cluster.orm.id) is cluster.orm
    lock.assert_not_called()
    archive.assert_not_called()


def test_cluster_can_be_deleted_after_missing_github_template(app, mocker):
    from github import GithubException
    from mchub.database import db
    from mchub.models.magic_castle.magic_castle import MagicCastle, MagicCastleORM
    from mchub.models.magic_castle.cluster_status_code import ClusterStatusCode
    from mchub.services.github_api import GithubStorage, get_github_storage

    storage = get_github_storage()
    mocker.patch.object(storage, "create_repo", side_effect=GithubException(404, "Template not found"))
    cluster = MagicCastle()
    with pytest.raises(GithubException):
        cluster.plan_creation(deepcopy(VALID_CLUSTER_CONFIGURATION))
    assert cluster.orm.undeployed
    assert not cluster.tfcloud_workspace
    assert cluster.orm.creation_step == "github_repository"
    # The background worker records the failed creation status.
    cluster.status = ClusterStatusCode.PLAN_ERROR
    cluster_id = cluster.orm.id
    real_storage = GithubStorage.__new__(GithubStorage)
    real_storage.organization = "test-org"
    real_storage.github = mocker.Mock()
    real_storage.github.get_organization.return_value.get_repo.side_effect = GithubException(404, "Not found")
    mocker.patch("mchub.models.magic_castle.magic_castle.get_github_storage", return_value=real_storage)
    from types import SimpleNamespace
    from mchub.resources.magic_castle_api import MagicCastleAPI
    user = SimpleNamespace(projects=[cluster.project], can_access_cluster=lambda orm: True)
    assert MagicCastleAPI().delete(user, cluster.hostname) == ({}, 204)
    assert db.session.get(MagicCastleORM, cluster_id) is None
