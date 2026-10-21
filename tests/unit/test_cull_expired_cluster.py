from datetime import datetime

import pytest

from mchub.database import db
from mchub.exceptions.invalid_usage_exception import BusyClusterException, InvalidUsageException
from mchub.models.magic_castle.magic_castle import MagicCastle, MagicCastleORM
from mchub.models.magic_castle.cluster_status_code import ClusterStatusCode as Status
from mchub.models.magic_castle.terraform_cloud_status import TFCloudStatusCode
from mchub.services import cull_expired_cluster as cull
from mchub.services import cluster_lifecycle as lifecycle
from tests.unit.test_usage import app, cluster, config_mock  # noqa: F401


@pytest.fixture
def expired(cluster, mocker):
    cluster.undeployed = False
    cluster.expiration_date = "2020-01-01"
    cluster.status = Status.PROVISIONING_SUCCESS
    cluster.tfcloud_run.plan = {"resource_changes": []}
    db.session.commit()
    mocker.patch.object(MagicCastle, "_update_status_from_tf_cloud")
    mocker.patch.object(cull.service_status, "read_status", return_value={"providers": [
        {"provider": name, "name": name, "reported_status": "no_incidents",
         "freshness": "fresh", "last_attempt_ok": True}
        for name in ("github", "terraform_cloud")
    ]})
    mocker.patch.object(cull.agent_health, "read_availability", return_value={"available": True, "message": ""})
    mocker.patch.object(cull, "get_terraform_cloud").return_value.ensure_agent_available.return_value = None
    return cluster


def test_expiration_plans_and_applies_exact_destroy_run(expired, mocker):
    def plan(hostname, timeout):
        assert expired.status == Status.BACKGROUND_TASK_RUNNING
        assert timeout == cull.PLAN_WAIT_TIMEOUT
        expired.status = Status.CREATED
        expired.tfcloud_run.run_id = "destroy-run"
        db.session.commit()
    mocker.patch.object(lifecycle, "plan_teardown", side_effect=plan)
    tf = mocker.Mock()
    tf.get_run_status.return_value = (None, True)
    mocker.patch.object(lifecycle, "get_terraform_cloud", return_value=tf)
    apply = mocker.patch.object(MagicCastle, "apply")
    cull.expire_cluster(expired, datetime.now())
    tf.get_run_status.assert_called_once_with("destroy-run")
    apply.assert_called_once_with(initiated_by=None)
    assert expired.creation_step is None


@pytest.mark.parametrize("status,undeployed,expiration", [
    (Status.CREATED, True, "2020-01-01"),
    (Status.PROVISIONING_SUCCESS, False, None),
    (Status.PROVISIONING_SUCCESS, False, "2999-01-01"),
])
def test_skips_undeployed_or_unexpired(expired, mocker, status, undeployed, expiration):
    expired.status, expired.undeployed, expired.expiration_date = status, undeployed, expiration
    db.session.commit()
    plan = mocker.patch.object(lifecycle, "plan_teardown")
    cull.expire_cluster(expired, datetime.now())
    plan.assert_not_called()


@pytest.mark.parametrize("status", [Status.BACKGROUND_TASK_RUNNING, Status.PLAN_RUNNING, Status.BUILD_RUNNING, Status.DESTROY_RUNNING])
def test_busy_clusters_are_not_claimed(expired, mocker, status):
    expired.status = status
    db.session.commit()
    plan = mocker.patch.object(lifecycle, "plan_teardown")
    with pytest.raises(BusyClusterException):
        cull.expire_cluster(expired, datetime.now())
    plan.assert_not_called()


def test_empty_teardown_does_not_apply(expired, mocker):
    mocker.patch.object(lifecycle, "plan_teardown", side_effect=lambda hostname, *_: MagicCastle(lifecycle.get_cluster(hostname)).complete_teardown())
    apply = mocker.patch.object(lifecycle, "apply_cluster")
    cull.expire_cluster(expired, datetime.now())
    assert expired.undeployed
    apply.assert_not_called()


def test_failed_plan_releases_claim_and_never_applies(expired, mocker):
    mocker.patch.object(lifecycle, "plan_teardown", side_effect=TimeoutError("plan timeout"))
    apply = mocker.patch.object(lifecycle, "apply_cluster")
    with pytest.raises(TimeoutError):
        cull.expire_cluster(expired, datetime.now())
    assert expired.status == Status.PLAN_ERROR
    assert expired.creation_step is None
    apply.assert_not_called()


def test_expiration_extension_during_planning_cancels_apply(expired, mocker):
    def plan(*_):
        expired.status = Status.CREATED
        expired.expiration_date = "2999-01-01"
        db.session.commit()
    mocker.patch.object(lifecycle, "plan_teardown", side_effect=plan)
    apply = mocker.patch.object(lifecycle, "apply_cluster")
    cull.expire_cluster(expired, datetime.now())
    apply.assert_not_called()


@pytest.mark.parametrize("changed_run,is_destroy", [(True, True), (False, False)])
def test_never_applies_replaced_or_non_destroy_plan(expired, mocker, changed_run, is_destroy):
    apply = mocker.patch.object(MagicCastle, "apply")
    tf = mocker.patch.object(lifecycle, "get_terraform_cloud").return_value
    tf.get_run_status.return_value = (None, is_destroy)
    with pytest.raises(InvalidUsageException):
        lifecycle.apply_cluster(expired.hostname, expected_destroy_run="different-run" if changed_run else expired.tfcloud_run.run_id)
    apply.assert_not_called()


def test_sweep_isolates_cluster_errors(expired, mocker):
    # A per-cluster error is logged rather than taking down the worker loop.
    expire = mocker.patch.object(cull, "expire_cluster", side_effect=RuntimeError("remote unavailable"))
    cull.poll_once()
    expire.assert_called_once()


def test_restart_recovers_only_expiration_owned_claim(expired):
    expired.status = Status.BACKGROUND_TASK_RUNNING
    expired.creation_step = "expiration"
    db.session.commit()
    cull.recover_interrupted_expiration()
    assert expired.status == Status.PLAN_RUNNING
    assert expired.creation_step is None
    expired.status = Status.BACKGROUND_TASK_RUNNING
    db.session.commit()
    cull.recover_interrupted_expiration()
    assert expired.status == Status.BACKGROUND_TASK_RUNNING


def test_claim_detects_expiration_change_since_read(expired):
    db.session.execute(db.update(type(expired)).where(type(expired).id == expired.id)
                       .values(expiration_date="2999-01-01").execution_options(synchronize_session=False))
    with pytest.raises(BusyClusterException):
        lifecycle.claim_background_task(expired)


def test_destroy_plan_polling_deadline_releases_failed_plan(expired, mocker):
    tf = mocker.patch("mchub.models.magic_castle.magic_castle.get_terraform_cloud").return_value
    tf.get_run_plan_log_json.return_value = None
    mocker.patch("mchub.models.magic_castle.magic_castle.time.monotonic", side_effect=[0, 301])
    with pytest.raises(TimeoutError, match="Timed out"):
        MagicCastle(expired).create_plan(run_id="destroy-run", timeout=300)
    assert expired.status == Status.PLAN_ERROR


@pytest.mark.parametrize("provider", ["github", "terraform_cloud"])
@pytest.mark.parametrize("condition", ["disruption", "stale", "unknown", "failed_check"])
def test_provider_outage_defers_before_refresh_or_plan(expired, mocker, provider, condition):
    status = next(p for p in cull.service_status.read_status.return_value["providers"] if p["provider"] == provider)
    if condition == "disruption":
        status["reported_status"] = "disruption"
    elif condition == "failed_check":
        status["last_attempt_ok"] = False
    else:
        status["freshness"] = condition
    plan = mocker.patch.object(lifecycle, "plan_teardown")
    cluster_id = expired.id
    previous_run = expired.tfcloud_run.run_id
    cull.poll_once()
    plan.assert_not_called()
    MagicCastle._update_status_from_tf_cloud.assert_not_called()
    cull.get_terraform_cloud.assert_not_called()
    expired = db.session.get(MagicCastleORM, cluster_id)
    assert expired.status == Status.PROVISIONING_SUCCESS
    assert expired.tfcloud_run.run_id == previous_run
    assert expired.expiration_date == "2020-01-01"


@pytest.mark.parametrize("live", [False, True])
def test_agent_outage_defers_without_claiming_cluster(expired, mocker, live):
    if live:
        cull.get_terraform_cloud.return_value.ensure_agent_available.side_effect = InvalidUsageException("Agent down", 503)
    else:
        cull.agent_health.read_availability.return_value = {"available": False, "message": "Agent down or unknown"}
    plan = mocker.patch.object(lifecycle, "plan_teardown")
    with pytest.raises(cull.ExpirationDeferred):
        cull.expire_cluster(expired, datetime.now())
    plan.assert_not_called()
    assert expired.status == Status.PROVISIONING_SUCCESS
    assert expired.creation_step is None


@pytest.mark.parametrize("dependency", ["github", "terraform_cloud", "agent", "live_agent"])
def test_outage_after_planning_preserves_and_resumes_same_destroy_plan(expired, mocker, dependency):
    cluster_id = expired.id
    provider = cull.service_status.read_status.return_value["providers"][dependency == "terraform_cloud"]
    def plan(*_):
        expired.status = Status.CREATED
        expired.tfcloud_run.run_id = "destroy-run"
        db.session.commit()
        if dependency == "agent":
            cull.agent_health.read_availability.return_value = {"available": False, "message": "Agent down"}
        elif dependency == "live_agent":
            cull.get_terraform_cloud.return_value.ensure_agent_available.side_effect = InvalidUsageException("Agent down", 503)
        else:
            provider["reported_status"] = "disruption"
    plan_mock = mocker.patch.object(lifecycle, "plan_teardown", side_effect=plan)
    apply = mocker.patch.object(MagicCastle, "apply")
    cull.poll_once()
    expired = db.session.get(MagicCastleORM, cluster_id)
    assert expired.status == Status.CREATED
    assert expired.tfcloud_run.run_id == "destroy-run"
    apply.assert_not_called()
    # A later sweep after recovery applies the saved destroy plan, not a new run.
    provider["reported_status"] = "no_incidents"
    cull.agent_health.read_availability.return_value = {"available": True, "message": ""}
    cull.get_terraform_cloud.return_value.ensure_agent_available.side_effect = None
    cull.get_terraform_cloud.return_value.get_run_status.return_value = (TFCloudStatusCode.PLANNED, True)
    tf = mocker.patch.object(lifecycle, "get_terraform_cloud").return_value
    tf.get_run_status.return_value = (TFCloudStatusCode.PLANNED, True)
    cull.poll_once()
    assert plan_mock.call_count == 1
    apply.assert_called_once_with(initiated_by=None)
    tf.get_run_status.assert_called_once_with("destroy-run")


def test_recovery_retries_deferred_expiration(expired, mocker):
    cluster_id = expired.id
    availability = cull.agent_health.read_availability.return_value
    availability.update(available=False, message="Agent down")
    plan = mocker.patch.object(lifecycle, "plan_teardown", side_effect=lambda hostname, *_: MagicCastle(lifecycle.get_cluster(hostname)).complete_teardown())
    cull.poll_once()
    plan.assert_not_called()
    availability["available"] = True
    cull.poll_once()
    plan.assert_called_once()
    expired = db.session.get(MagicCastleORM, cluster_id)
    assert expired.undeployed


def test_expiration_extended_during_final_health_check_does_not_apply(expired, mocker):
    def plan(*_):
        expired.status = Status.CREATED
        expired.tfcloud_run.run_id = "destroy-run"
        db.session.commit()
    mocker.patch.object(lifecycle, "plan_teardown", side_effect=plan)
    def check(_):
        if expired.status == Status.CREATED:
            expired.expiration_date = "2999-01-01"
            db.session.commit()
    cull.get_terraform_cloud.return_value.ensure_agent_available.side_effect = check
    apply = mocker.patch.object(lifecycle, "apply_cluster")
    cull.expire_cluster(expired, datetime.now())
    apply.assert_not_called()


def test_disabled_provider_monitors_do_not_block_cleanup(expired):
    cull.service_status.read_status.return_value = {"providers": []}
    cull.ensure_expiration_ready(expired)
    cull.get_terraform_cloud.return_value.ensure_agent_available.assert_called_once_with(expired.project)


@pytest.mark.parametrize("remote_status", [TFCloudStatusCode.PENDING, TFCloudStatusCode.APPLYING, TFCloudStatusCode.APPLIED])
def test_changed_remote_destroy_run_is_not_replaced(expired, mocker, remote_status):
    expired.status = Status.CREATED
    expired.tfcloud_run.run_id = "destroy-run"
    db.session.commit()
    cull.get_terraform_cloud.return_value.get_run_status.return_value = (remote_status, True)
    plan = mocker.patch.object(lifecycle, "plan_teardown")
    with pytest.raises(BusyClusterException):
        cull.expire_cluster(expired, datetime.now())
    plan.assert_not_called()
