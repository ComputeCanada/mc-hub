from datetime import datetime

import pytest

from mchub.database import db
from mchub.exceptions.invalid_usage_exception import BusyClusterException, InvalidUsageException
from mchub.models.magic_castle.magic_castle import MagicCastle
from mchub.models.magic_castle.cluster_status_code import ClusterStatusCode as Status
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
    mocker.patch.object(lifecycle, "plan_teardown", side_effect=lambda *_: MagicCastle(expired).complete_teardown())
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
