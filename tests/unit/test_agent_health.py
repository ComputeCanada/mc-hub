import importlib
from types import SimpleNamespace

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect

from mchub.database import db
from mchub.models.agent_health import AgentHealthSnapshot
from mchub.models.notification import NotificationEvent, NotificationDelivery
from mchub.services import agent_health as health
from mchub.services import notifications
from tests.unit.test_service_status import app, config_mock


@pytest.fixture
def monitor(app, mocker):
    config = {"tfcloud_organization": "org", "openstack_clouds": [
        {"auth_url": "https://cloud", "agent_pool_name": "pool"},
        {"auth_url": "https://other", "agent_pool_name": "pool"},
        {"auth_url": "https://remote"},
    ]}
    mocker.patch.object(health, "get_config", return_value=config)
    mocker.patch("mchub.services.terraform_cloud_api.get_config", return_value=config)
    clock = mocker.patch.object(health.time, "time", return_value=1000)
    client = mocker.patch.object(health, "get_terraform_cloud").return_value
    targets = mocker.patch.object(notifications, "destinations", return_value=[{"id": "ops"}])
    client.check_agent_pool.return_value = result("healthy")
    return clock, client.check_agent_pool, targets, config


def result(status):
    return {"status": status, "available": status == "healthy", "message": "" if status == "healthy" else status}


def events():
    return db.session.scalars(db.select(NotificationEvent).order_by(NotificationEvent.created_at)).all()


def project():
    return SimpleNamespace(provider="openstack", env={"OS_AUTH_URL": "https://cloud"})


def test_monitor_runs_without_visitors_deduplicates_pool_and_events_across_sessions(monitor):
    clock, check, _, _ = monitor
    health.poll_once()
    check.assert_called_once_with("pool")
    assert not events()
    assert health.read_availability(project()) == {"available": True, "message": ""}
    clock.return_value = 1299
    health.poll_once()
    assert check.call_count == 1
    clock.return_value = 1300
    check.return_value = result("unavailable")
    health.poll_once()
    assert [e.event_type for e in events()] == ["agent_pool.unavailable"]
    assert len(db.session.scalars(db.select(NotificationDelivery)).all()) == 1
    db.session.remove()  # persistence, rather than process-local deduplication
    clock.return_value = 1330
    health.poll_once()
    assert check.call_count == 3
    assert len(events()) == 1
    clock.return_value = 1360
    check.return_value = result("healthy")
    health.poll_once()
    assert [e.event_type for e in events()] == ["agent_pool.unavailable", "agent_pool.recovered"]


def test_read_is_cached_and_fails_closed_for_missing_stale_or_unknown_status(monitor):
    clock, check, _, _ = monitor
    assert not health.read_availability(project())["available"]
    check.assert_not_called()
    health.poll_once()
    for _ in range(10):
        assert health.read_availability(project())["available"]
    assert check.call_count == 1
    clock.return_value = 1661
    assert not health.read_availability(project())["available"]
    assert check.call_count == 1
    check.return_value = result("unknown")
    health.poll_once()
    assert not health.read_availability(project())["available"]
    assert events()[0].event_type == "agent_pool.check_failed"
    clock.return_value = 1691
    health.poll_once()
    assert len(events()) == 1


def test_no_pool_skips_snapshot_and_terraform(monitor):
    _, check, _, config = monitor
    config["openstack_clouds"] = []
    health.poll_once()
    assert health.read_availability(project())["available"]
    assert health.read_availability(SimpleNamespace(provider="aws"))["available"]
    check.assert_not_called()


def test_enabling_notifications_during_outage_alerts_on_next_check(monitor):
    clock, check, targets, _ = monitor
    targets.return_value = []
    check.return_value = result("unavailable")
    health.poll_once()
    assert not events()
    targets.return_value = [{"id": "ops"}]
    clock.return_value = 1030
    health.poll_once()
    assert events()[0].event_type == "agent_pool.unavailable"


def test_state_and_notification_commit_together(monitor, mocker):
    _, check, _, _ = monitor
    check.return_value = result("unavailable")
    commit = mocker.patch.object(db.session, "commit", side_effect=RuntimeError)
    health.poll_once()
    mocker.stop(commit)
    assert not events()
    assert db.session.get(AgentHealthSnapshot, ("org", "pool")) is None
    health.poll_once()
    assert len(events()) == 1


def test_one_pool_failure_does_not_stop_other_pools(monitor):
    _, check, _, config = monitor
    config["openstack_clouds"].append({"auth_url": "https://third", "agent_pool_name": "pool2"})
    check.side_effect = [RuntimeError("unexpected"), result("healthy")]
    health.poll_once()
    assert check.call_count == 2
    assert db.session.get(AgentHealthSnapshot, ("org", "pool2")).status == "healthy"


def test_migration_round_trip():
    migration = importlib.import_module("migrations.versions.0025_agent_health")
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
            assert "agent_health_snapshot" in inspect(connection).get_table_names()
            migration.downgrade()
            assert "agent_health_snapshot" not in inspect(connection).get_table_names()


def test_monitor_is_supervised():
    from mchub.services.background_worker import MODULES
    assert "mchub.services.agent_health_monitor" in MODULES
