from datetime import timedelta
import importlib

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, text

from tests.test_helpers import app, generate_test_clusters, mock_github_storage_api, mock_terraform_cloud_api
from tests.mocks.configuration.config_mock import config_auth_none_mock as config_mock
from mchub.database import db
from mchub.models.magic_castle.magic_castle import MagicCastle, MagicCastleORM
from mchub.models.magic_castle.cluster_status_code import ClusterStatusCode as Status
from mchub.models.terraform_cloud import TerraformCloudRunORM
from mchub.services import plan_recovery as recovery
from mchub.services.github_api import get_github_storage
from mchub.services.terraform_cloud_api import get_terraform_cloud


@pytest.fixture
def interrupted(app, mocker):
    orm = db.session.scalar(db.select(MagicCastleORM).filter_by(hostname="valid1.magic-castle.cloud"))
    orm.status = Status.BACKGROUND_TASK_RUNNING
    orm.tfcloud_workspace = "ws-recovery"
    orm.tfcloud_run = TerraformCloudRunORM()
    db.session.commit()
    variables = {"cluster_name": "test", "instances": {"login": {"count": 2}}, "hieradata": ""}
    mocker.patch.object(MagicCastle, "_get_var_tf", return_value=variables)
    storage, tf = get_github_storage(), get_terraform_cloud()
    mocker.patch.object(storage, "get_plan_configuration", create=True, return_value=("october-16-sha", variables))
    mocker.patch.object(storage, "trigger_run", create=True, return_value=False)
    mocker.patch.object(tf, "find_recovery_run", create=True, return_value="october-16-run")
    mocker.patch.object(tf, "unblock_recovery_run", create=True)
    return MagicCastle(orm), storage, tf


def test_legacy_missing_sha_recovers_verified_configuration(interrupted):
    cluster, storage, tf = interrupted
    recovery.recover(cluster)
    assert cluster.tfcloud_run.commit_sha == "october-16-sha"
    assert cluster.tfcloud_run.run_id == "october-16-run"
    assert cluster.orm.status == Status.PLAN_RUNNING
    assert cluster.tfcloud_run.lease_owner is None
    tf.find_recovery_run.assert_called_once_with("ws-recovery", "october-16-sha")
    tf.unblock_recovery_run.assert_called_once_with("ws-recovery", "october-16-run")
    storage.get_plan_configuration.assert_called_once_with(cluster.hostname, require_tag=True)
    # Once reconciled, observation doesn't repeat queue mutations.
    recovery.recover(cluster)
    assert tf.unblock_recovery_run.call_count == 1


@pytest.mark.parametrize("saved", [None, ("different-sha", {"cluster_name": "different"})])
def test_legacy_mismatch_does_not_select_latest_run(interrupted, saved):
    cluster, storage, tf = interrupted
    storage.get_plan_configuration.return_value = saved
    recovery.recover(cluster)
    assert cluster.tfcloud_run.run_id is None
    assert cluster.orm.status == Status.BACKGROUND_TASK_RUNNING
    storage.trigger_run.assert_not_called()
    tf.find_recovery_run.assert_not_called()
    tf.unblock_recovery_run.assert_not_called()


def test_live_lease_prevents_recovery_until_expiry(interrupted):
    cluster, storage, tf = interrupted
    owner = recovery.acquire(cluster.tfcloud_run)
    recovery.recover(cluster)
    storage.get_plan_configuration.assert_not_called()
    cluster.tfcloud_run.lease_until = recovery.now() - timedelta(seconds=1)
    db.session.commit()
    recovery.recover(cluster)
    assert cluster.tfcloud_run.run_id == "october-16-run"
    assert not recovery.renew(cluster.tfcloud_run.id, owner)


def test_old_owner_cannot_release_replacement_lease(interrupted):
    cluster, _, _ = interrupted
    run = cluster.tfcloud_run
    first = recovery.acquire(run)
    run.lease_until = recovery.now() - timedelta(seconds=1)
    db.session.commit()
    second = recovery.acquire(run)
    assert second and second != first
    recovery.release(run.id, first)
    assert run.lease_owner == second
    assert not recovery.renew(run.id, first)


def test_queue_failure_preserves_intent_for_retry(interrupted):
    cluster, storage, tf = interrupted
    tf.unblock_recovery_run.side_effect = RuntimeError("temporary API failure")
    recovery.recover(cluster)
    assert cluster.tfcloud_run.run_id == "october-16-run"
    assert cluster.tfcloud_run.intent_hash
    tf.unblock_recovery_run.side_effect = None
    recovery.recover(cluster)
    assert cluster.tfcloud_run.intent_hash is None
    assert storage.get_plan_configuration.call_count == 1
    assert tf.find_recovery_run.call_count == 1


def test_persisted_commit_does_not_follow_new_repository_head(interrupted):
    cluster, storage, tf = interrupted
    cluster.tfcloud_run.commit_sha = "original-intended-sha"
    cluster.tfcloud_run.intent_hash = "commit"
    cluster.orm.status = Status.PLAN_ERROR
    db.session.commit()
    recovery.recover(cluster)
    storage.get_plan_configuration.assert_not_called()
    tf.find_recovery_run.assert_called_once_with("ws-recovery", "original-intended-sha")


def test_crash_before_trigger_recovers_untagged_commit_by_fingerprint(interrupted):
    cluster, storage, _ = interrupted
    cluster.tfcloud_run.intent_hash = recovery.fingerprint(cluster._get_var_tf())
    db.session.commit()
    recovery.recover(cluster)
    storage.get_plan_configuration.assert_called_once_with(cluster.hostname, require_tag=False)
    storage.trigger_run.assert_called_once_with(cluster.hostname, "october-16-sha")


def test_commit_persisted_before_waiting_for_run(interrupted, mocker):
    cluster, _, tf = interrupted
    def interrupted_lookup(workspace, sha):
        row = db.session.execute(text("SELECT commit_sha FROM terraformcloudrun WHERE magic_castle_id = :id"), {"id": cluster.orm.id}).one()
        assert row.commit_sha == "intended-sha"
        raise SystemExit("worker terminated")
    mocker.patch.object(tf, "get_run_by_commit", side_effect=interrupted_lookup)
    with pytest.raises(SystemExit):
        cluster.create_plan(github_sha="intended-sha")
    assert cluster.tfcloud_run.commit_sha == "intended-sha"
    assert cluster.tfcloud_run.intent_hash


def test_write_persists_inputs_and_commit_before_tag(interrupted, mocker):
    cluster, storage, _ = interrupted
    variables = cluster._get_var_tf()
    def write(data, hostname, on_commit):
        assert cluster.tfcloud_run.intent_hash == recovery.fingerprint(data)
        assert cluster.tfcloud_run.lease_owner
        on_commit("new-sha")
        assert cluster.tfcloud_run.commit_sha == "new-sha"
        raise RuntimeError("tag request failed")
    mocker.patch.object(storage, "write", side_effect=write)
    with pytest.raises(RuntimeError):
        cluster._write_plan_configuration(variables)
    assert cluster.tfcloud_run.commit_sha == "new-sha"
    assert cluster.tfcloud_run.lease_owner is None


def test_legacy_proxy_token_only_ignores_generated_ciphertext():
    def variables(token, count=1, workspace="ws-1"):
        return {"count": count, "hieradata": "user::secret: ENC[unchanged]\n"
                f"profile::slurm::controller::tfe_token: ENC[{token}]\n"
                f"profile::slurm::controller::tfe_workspace: {workspace}\n"
                "profile::slurm::controller::tfe_proxy_url: https://hub/api/tfcloud-proxy"}
    assert recovery.legacy_variables(variables("a")) == recovery.legacy_variables(variables("b"))
    assert recovery.legacy_variables(variables("a")) != recovery.legacy_variables(variables("a", count=2))
    assert recovery.legacy_variables(variables("a")) != recovery.legacy_variables(variables("a", workspace="other"))


def test_migration_preserves_missing_run_legacy_record():
    migration = importlib.import_module("migrations.versions.0024_plan_recovery")
    with create_engine("sqlite://").begin() as conn:
        conn.execute(text("CREATE TABLE terraformcloudrun (id INTEGER PRIMARY KEY, run_id TEXT, commit_sha TEXT)"))
        conn.execute(text("INSERT INTO terraformcloudrun VALUES (1, NULL, NULL)"))
        with Operations.context(MigrationContext.configure(conn)):
            migration.upgrade()
            assert tuple(conn.execute(text("SELECT * FROM terraformcloudrun")).one()) == (1, None, None, None, None, None)
            migration.downgrade()
            assert tuple(conn.execute(text("SELECT * FROM terraformcloudrun")).one()) == (1, None, None)


def test_expired_writer_cannot_overwrite_replacement_task(interrupted, mocker):
    from mchub.services.cluster_lifecycle import execute_claimed_task
    cluster, storage, _ = interrupted
    hostname = cluster.hostname
    replacement = "replacement-owner"
    def write(data, hostname, on_commit):
        run = cluster.tfcloud_run
        run.lease_owner = replacement
        run.lease_until = recovery.now() + timedelta(seconds=360)
        cluster.orm.status = Status.BACKGROUND_TASK_RUNNING
        cluster.orm.creation_step = "capacity"
        db.session.commit()
        on_commit("late-sha")
    mocker.patch.object(storage, "write", side_effect=write)
    execute_claimed_task(hostname, cluster._write_plan_configuration, cluster._get_var_tf())
    assert cluster.tfcloud_run.commit_sha is None
    assert cluster.tfcloud_run.lease_owner == replacement
    assert cluster.orm.status == Status.BACKGROUND_TASK_RUNNING
    assert cluster.orm.creation_step == "capacity"


def test_lease_is_visible_atomically_with_new_intent(interrupted, mocker):
    cluster, storage, _ = interrupted
    def write(data, hostname, on_commit):
        assert recovery.acquire(cluster.tfcloud_run) is None
        on_commit("saved-sha")
        return "saved-sha"
    mocker.patch.object(storage, "write", side_effect=write)
    assert cluster._write_plan_configuration(cluster._get_var_tf()) == "saved-sha"
    assert cluster.tfcloud_run.lease_owner == cluster._plan_owner
