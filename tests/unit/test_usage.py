import datetime as dt
import importlib
from types import SimpleNamespace
from unittest.mock import PropertyMock

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text
from freezegun import freeze_time

from mchub import create_app
from mchub.database import db
from mchub.models.cloud.project import Project
from mchub.models.user import UserORM
from mchub.models.magic_castle.magic_castle import MagicCastle, MagicCastleORM
from mchub.models.magic_castle.cluster_status_code import ClusterStatusCode as Status
from mchub.models.terraform_cloud import TerraformCloudRunORM
from mchub.models.usage import UsageApply, UsageLifetime
from mchub.services import usage
from mchub.services.usage_monitor import poll_once
from mchub.resources.usage_api import UsageAPI
from tests.mocks.configuration.config_mock import config_auth_saml_mock as config_mock
from tests.data import ALICE_HEADERS


@pytest.fixture
def app(config_mock):
    app = create_app("sqlite://")
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def cluster(app):
    project = Project(name="Research", provider="openstack", github_template="x", tfcloud_project_id="p-1")
    owner = UserORM(scoped_id="owner@example.org")
    orm = MagicCastleORM(hostname="test.example.org", project=project, created_by=owner,
        undeployed=True, status=Status.CREATED, usage_repository="org/repo",
        tfcloud_run=TerraformCloudRunORM(run_id="run-1", commit_sha="abc123"))
    db.session.add(orm)
    db.session.commit()
    return orm


def report(app, query=""):
    with app.test_request_context("/api/usage" + query):
        return UsageAPI().get(SimpleNamespace(is_admin=True))


def test_lifetime_rebuild_update_and_deletion(app, cluster):
    with freeze_time("2026-01-01 10:00:00"):
        attempt = usage.begin_apply(cluster, "operator@example.org")
        usage.accepted(attempt)
        assert usage.begin_apply(cluster).id == attempt.id
    with freeze_time("2026-01-01 10:05:00"):
        cluster.status = Status.PROVISIONING_SUCCESS
        usage.observe(cluster)
        db.session.commit()
    with freeze_time("2026-01-01 11:00:00"):
        usage.observe(cluster)
        assert attempt.healthy_at == dt.datetime(2026, 1, 1, 10, 5)
        cluster.tfcloud_run = TerraformCloudRunORM(run_id="run-update")
        db.session.commit()
        update = usage.begin_apply(cluster)
        usage.accepted(update)
        assert update.kind == "update"
    with freeze_time("2026-01-01 11:10:00"):
        usage.observe(cluster)
        db.session.commit()
    with freeze_time("2026-01-02 10:00:00"):
        MagicCastle(cluster).complete_teardown()
    with freeze_time("2026-02-01 10:00:00"):
        cluster.tfcloud_run = TerraformCloudRunORM(run_id="run-rebuild")
        db.session.commit()
        rebuild = usage.begin_apply(cluster)
        usage.accepted(rebuild)
        assert rebuild.kind == "deployment"
    with freeze_time("2026-02-01 10:15:00"):
        cluster.status = Status.PROVISIONING_SUCCESS
        usage.observe(cluster)
        db.session.commit()
    with freeze_time("2026-02-02 10:00:00"):
        MagicCastle(cluster).complete_teardown()
        db.session.delete(cluster.project)  # cascades cluster, but never analytics
        db.session.commit()
        data = report(app, "?start=2026-01-01&end=2026-02-28")
    assert data["summary"] == dict(successful_deployments=2, distinct_clusters=1,
        unique_creators=1, first_time_creators=1, returning_creators=0, active_projects=1)
    assert data["months"][1]["returning_creators"] == 1
    assert data["apply_to_healthy"] == dict(count=3, average_seconds=600, median_seconds=600, p95_seconds=900)
    assert data["completed_lifetime"]["average_seconds"] == 86400
    assert data["attempts"][-1]["initiated_by"] == "operator@example.org"
    assert data["attempts"][-1]["commit_sha"] == "abc123"
    assert len(db.session.scalars(db.select(UsageLifetime)).all()) == 2


def test_failed_pending_and_legacy_excluded_from_timing(app, cluster):
    with freeze_time("2026-01-01"):
        cluster.usage_legacy = True
        cluster.undeployed = False
        attempt = usage.begin_apply(cluster)
        usage.accepted(attempt)
        cluster.status = Status.PROVISIONING_ERROR
        usage.observe(cluster)
        db.session.commit()
        cluster.tfcloud_run = TerraformCloudRunORM(run_id="run-pending")
        db.session.commit()
        usage.begin_apply(cluster)
        data = report(app, "?start=2026-01-01&end=2026-01-31")
    assert data["failed_attempts"] == 1
    assert data["unfinished_attempts"] == 1
    assert data["apply_to_healthy"]["count"] == 0
    assert data["legacy_lifetimes"] == 1
    assert data["summary"]["successful_deployments"] == 0
    assert usage.current_lifetime(cluster).started_at is None


def test_background_observer_records_readiness_without_requests(app, cluster, mocker):
    with freeze_time("2026-01-01"):
        attempt = usage.begin_apply(cluster)
        usage.accepted(attempt)
        cluster.status = Status.PROVISIONING_RUNNING
        db.session.commit()
    mocker.patch.object(MagicCastle, "_update_status_from_tf_cloud")
    mocker.patch.object(MagicCastle, "services_are_online", new_callable=PropertyMock, return_value=True)
    with freeze_time("2026-01-01 00:02:00"):
        poll_once()
        data = report(app, "?start=2026-01-01&end=2026-01-31")
    assert data["apply_to_healthy"]["average_seconds"] == 120
    assert data["last_poll_at"] == "2026-01-01T00:02:00Z"


def test_admin_only_and_validation(app):
    client = app.test_client()
    assert client.get("/api/usage").status_code == 400
    assert client.get("/api/usage", headers=ALICE_HEADERS).status_code == 403
    admin = {**ALICE_HEADERS, "eduPersonPrincipalName": "the-admin@computecanada.ca"}
    assert client.get("/api/usage", headers=admin).status_code == 200
    for query in ("?start=bad", "?start=2026-02-01&end=2026-01-01", "?page=0", "?page=no", "?end=9999-12-31"):
        assert client.get("/api/usage" + query, headers=admin).status_code == 400


def test_migration_roundtrip():
    migration = importlib.import_module("migrations.versions.0011_usage_history")
    with create_engine("sqlite://").begin() as connection:
        for table in ("magiccastle", "project", "terraformcloudrun"):
            connection.execute(text(f"CREATE TABLE {table} (id INTEGER PRIMARY KEY)"))
            connection.execute(text(f"INSERT INTO {table} VALUES (1), (2)"))
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
            ids = connection.execute(text("SELECT usage_id FROM magiccastle")).scalars().all()
            assert len(set(ids)) == 2
            assert connection.execute(text("SELECT usage_legacy FROM magiccastle")).scalars().all() == [1, 1]
            assert connection.execute(text("SELECT tracking_started_at FROM usage_state")).scalar()
            migration.downgrade()
        assert set(inspect(connection).get_table_names()) == {"magiccastle", "project", "terraformcloudrun"}


def test_project_filter_uses_global_first_deployment_and_inclusive_dates(app, cluster):
    with freeze_time("2025-12-31 23:59:59"):
        usage.accepted(usage.begin_apply(cluster))
        cluster.status = Status.PROVISIONING_SUCCESS
        usage.observe(cluster)
        db.session.commit()
        usage.end_lifetime(cluster)
        db.session.commit()
    project = Project(name="Other", provider="openstack", github_template="x", tfcloud_project_id="p-other")
    cluster.project = project
    cluster.tfcloud_run = TerraformCloudRunORM(run_id="run-other")
    db.session.commit()
    with freeze_time("2026-01-31 23:59:59"):
        usage.accepted(usage.begin_apply(cluster))
        cluster.status = Status.PROVISIONING_SUCCESS
        usage.observe(cluster)
        db.session.commit()
    data = report(app, f"?start=2026-01-01&end=2026-01-31&project={project.usage_id}")
    assert data["summary"]["successful_deployments"] == 1
    assert data["summary"]["returning_creators"] == 1
    assert data["summary"]["first_time_creators"] == 0
    assert data["attempt_count"] == 1
    assert len(data["projects"]) == 2


def test_apply_captures_only_accepted_requests(app, cluster, mocker):
    castle = MagicCastle(cluster)
    cluster.tfcloud_run.plan = {"resource_changes": []}
    cluster.undeployed = False
    db.session.commit()
    mocker.patch.object(MagicCastle, "is_busy", new_callable=PropertyMock, return_value=False)
    tf = mocker.Mock()
    tf.get_run_status.return_value = (None, False)
    mocker.patch("mchub.models.magic_castle.magic_castle.get_terraform_cloud", return_value=tf)
    tf.apply_run.side_effect = RuntimeError("Connection lost")
    with pytest.raises(RuntimeError):
        castle.apply(initiated_by="actor@example.org")
    attempt = db.session.scalar(db.select(UsageApply))
    assert attempt.applied_at is None
    assert attempt.initiated_by == "actor@example.org"
    tf.apply_run.side_effect = None
    with freeze_time("2026-01-01"):
        castle.apply(initiated_by="actor@example.org")
    assert attempt.applied_at == dt.datetime(2026, 1, 1)
    assert len(db.session.scalars(db.select(UsageApply)).all()) == 1


def test_unknown_acceptance_never_invents_duration_or_lifetime_start(app, cluster):
    with freeze_time("2026-01-01"):
        attempt = usage.begin_apply(cluster)
    with freeze_time("2026-01-01 00:02:00"):
        cluster.status = Status.PROVISIONING_SUCCESS
        usage.observe(cluster)
        db.session.commit()
        # Acceptance response arrives after a concurrent healthy observation.
        usage.accepted(attempt)
        assert attempt.outcome == "successful"
        assert attempt.applied_at is None
        cluster.tfcloud_run = TerraformCloudRunORM(run_id="run-later-update")
        db.session.commit()
        usage.accepted(usage.begin_apply(cluster))
        assert usage.current_lifetime(cluster).started_at is None
        data = report(app, "?start=2026-01-01&end=2026-01-31")
        assert data["summary"]["successful_deployments"] == 1
        assert data["apply_to_healthy"]["count"] == 0


def test_timeout_can_recover_without_overwriting_first_healthy(app, cluster):
    with freeze_time("2026-01-01"):
        attempt = usage.begin_apply(cluster)
        usage.accepted(attempt)
        cluster.status = Status.PROVISIONING_ERROR
        usage.observe(cluster)
        db.session.commit()
        assert attempt.outcome == "failed"
    with freeze_time("2026-01-01 01:00:00"):
        cluster.status = Status.PROVISIONING_SUCCESS
        usage.observe(cluster)
        db.session.commit()
        assert attempt.outcome == "successful"
    with freeze_time("2026-01-02"):
        usage.observe(cluster)
        db.session.commit()
        assert attempt.healthy_at == dt.datetime(2026, 1, 1, 1)
