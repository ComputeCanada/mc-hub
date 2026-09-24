import importlib
import time

import pytest
from freezegun import freeze_time
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect

from mchub.database import db
from mchub.models.capacity_plan import CapacityPlan, CapacityQuotaCheck
from mchub.models.notification import NotificationEvent, NotificationDelivery
from mchub.models.magic_castle.cluster_status_code import ClusterStatusCode as Status
from mchub.services import capacity_preflight as preflight
from mchub.services import notifications
from tests.unit.test_capacity import app, cluster, config_mock, plan  # noqa: F401

TARGETS = [{"id": "ops", "type": "webhook", "url": "https://example.com/events"}]


@pytest.fixture
def due(plan, mocker):
    plan.starts_at = time.time() + 86400
    plan.ends_at = plan.starts_at + 86400
    db.session.commit()
    mocker.patch.object(preflight, "CloudManager")
    mocker.patch.object(preflight, "budget", return_value={"vcpus": 3})
    mocker.patch.object(notifications, "destinations", return_value=TARGETS)
    return plan


def events():
    return db.session.scalars(db.select(NotificationEvent)).all()


def add_plan(due, starts_at, ends_at, demand):
    row = CapacityPlan(project=due.project, owner=due.owner, starts_at=starts_at, ends_at=ends_at,
                       definition={"cluster_name": "second", "guest_passwd": "do-not-send"},
                       demand=demand, auto_create=False, status="planned")
    db.session.add(row); db.session.commit()
    return row


def test_shortage_enqueues_one_alert_and_delivery_without_secrets(due):
    preflight.check_project(due.project_id)
    event = events()[0]
    assert event.event_type == "capacity.quota_insufficient"
    assert event.payload["checks"][0]["shortages"] == {"vcpus": 1}
    assert "guest_passwd" not in str(event.payload)
    assert db.session.scalar(db.select(NotificationDelivery)).destination_id == "ops"
    preflight.check_project(due.project_id)
    assert len(events()) == 1
    assert db.session.get(CapacityQuotaCheck, due.project_id).result["status"] == "insufficient"


def test_overlapping_plans_checked_together_and_manual_plans_included(due, mocker):
    mocker.patch.object(preflight, "budget", return_value={"vcpus": 6})
    second = add_plan(due, due.starts_at, due.ends_at, {"vcpus": 4, "gpus": 100})
    preflight.check_project(due.project_id)
    event = events()[0]
    assert len(event.payload["plans"]) == 2
    assert event.payload["checks"][0]["shortages"] == {"vcpus": 2}
    assert set(event.payload["checks"][0]["plan_ids"]) == {due.id, second.id}


def test_disjoint_plans_not_added_together(due, mocker):
    due.starts_at = time.time() + 1000; due.ends_at = time.time() + 2000
    db.session.commit()
    add_plan(due, due.ends_at, due.ends_at + 1000, {"vcpus": 4})
    mocker.patch.object(preflight, "budget", return_value={"vcpus": 5})
    preflight.check_project(due.project_id)
    assert events() == []
    row = db.session.get(CapacityQuotaCheck, due.project_id)
    assert row.result["status"] == "sufficient"
    assert [check["required"]["vcpus"] for check in row.result["checks"]] == [4, 4]


def test_already_deployed_demand_is_in_current_usage(due, cluster):
    due.cluster_usage_id = cluster.usage_id
    cluster.undeployed = False; cluster.status = Status.PROVISIONING_SUCCESS
    db.session.commit()
    preflight.check_project(due.project_id)
    assert events() == []
    assert db.session.get(CapacityQuotaCheck, due.project_id).result["checks"][0]["required"] == {}


def test_existing_overlapping_plan_counts_towards_upcoming_start(due, mocker):
    add_plan(due, time.time() - 100, due.ends_at, {"vcpus": 3})
    mocker.patch.object(preflight, "budget", return_value={"vcpus": 6})
    preflight.check_project(due.project_id)
    assert events()[0].payload["checks"][0]["shortages"] == {"vcpus": 1}


@pytest.mark.parametrize("offset,status", [(86401, "planned"), (-1, "planned"), (3600, "cancelled")])
def test_only_non_cancelled_plans_starting_within_24_hours(due, mocker, offset, status):
    due.starts_at = time.time() + offset; due.status = status; db.session.commit()
    budget = mocker.patch.object(preflight, "budget")
    preflight.poll_once()
    assert events() == []
    budget.assert_not_called()


def test_unchanged_warning_not_repeated_after_hour_or_restart(due):
    project_id = due.project_id
    preflight.check_project(project_id)
    db.session.remove()
    with freeze_time(preflight.iso(time.time() + 3601)):
        preflight.check_project(project_id)
    assert len(events()) == 1


def test_changed_plan_rechecked_without_waiting_for_hour(due):
    preflight.check_project(due.project_id)
    due.demand = {"vcpus": 8}; db.session.commit()
    preflight.check_project(due.project_id)
    assert len(events()) == 2
    assert events()[1].payload["checks"][0]["shortages"] == {"vcpus": 5}


def test_cancelled_plan_clears_warning(due):
    preflight.check_project(due.project_id)
    due.status = "cancelled"; db.session.commit()
    preflight.check_project(due.project_id)
    assert db.session.get(CapacityQuotaCheck, due.project_id).result["status"] == "no_upcoming_plans"
    assert len(events()) == 1


def test_cloud_failure_is_unknown_and_retries_without_false_shortage(due, mocker):
    read = mocker.patch.object(preflight, "budget", side_effect=RuntimeError("secret credential"))
    preflight.check_project(due.project_id)
    row = db.session.get(CapacityQuotaCheck, due.project_id)
    assert row.result["status"] == "unknown"
    assert row.next_check_at - row.checked_at == 900
    assert "secret credential" not in str(row.result)
    assert events() == []
    read.side_effect = None; read.return_value = {"vcpus": 3}
    with freeze_time(preflight.iso(time.time() + 901)):
        preflight.check_project(due.project_id)
    assert len(events()) == 1


def test_without_destinations_warning_is_still_stored(due, mocker):
    mocker.patch.object(notifications, "destinations", return_value=[])
    preflight.check_project(due.project_id)
    assert events() == []
    assert db.session.get(CapacityQuotaCheck, due.project_id).result["status"] == "insufficient"


def test_edit_during_cloud_check_does_not_notify_stale_snapshot(due, mocker):
    def read(*args):
        due.status = "cancelled"; db.session.commit()
        return {"vcpus": 0}
    mocker.patch.object(preflight, "budget", side_effect=read)
    preflight.check_project(due.project_id)
    assert events() == []
    assert db.session.get(CapacityQuotaCheck, due.project_id) is None


def test_quota_check_migration_roundtrip():
    migration = importlib.import_module("migrations.versions.0022_capacity_quota_check")
    with create_engine("sqlite://").begin() as connection:
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
            assert "capacity_quota_check" in inspect(connection).get_table_names()
            migration.downgrade()
            assert "capacity_quota_check" not in inspect(connection).get_table_names()


def test_supervised_capacity_worker_runs_preflight(due):
    from mchub.services.capacity_worker import poll_once
    project_id = due.project_id
    poll_once()
    assert db.session.get(CapacityQuotaCheck, project_id).result["status"] == "insufficient"
    assert len(events()) == 1


def test_sufficient_quota_resets_alert_deduplication(due, mocker):
    available = mocker.patch.object(preflight, "budget", return_value={"vcpus": 3})
    preflight.check_project(due.project_id)
    available.return_value = {"vcpus": 10}
    with freeze_time(preflight.iso(time.time() + 3601)):
        preflight.check_project(due.project_id)
        assert db.session.get(CapacityQuotaCheck, due.project_id).result["status"] == "sufficient"
    available.return_value = {"vcpus": 3}
    with freeze_time(preflight.iso(time.time() + 7202)):
        preflight.check_project(due.project_id)
    assert len(events()) == 2
