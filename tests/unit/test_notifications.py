import importlib
import json
from urllib.error import HTTPError

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from marshmallow import ValidationError
from sqlalchemy import create_engine, inspect

from mchub.configuration import ConfigurationSchema
from mchub.database import db
from mchub.models.notification import NotificationDelivery, NotificationEvent
from mchub.models.service_status import ServiceStatusSnapshot
from mchub.services import notifications as notify, service_status as status
from tests.unit.test_service_status import app, config_mock, rss

TARGETS = [dict(id="ops", type="slack", url="https://hooks.slack.com/services/secret"),
           dict(id="automation", type="webhook", url="https://example.com/hook", token="secret")]


@pytest.fixture
def configured(app, mocker):
    mocker.patch.object(notify, "destinations", return_value=TARGETS)
    mocker.patch.object(status, "providers", return_value=[status.DEFAULT_PROVIDERS[1]])
    return mocker.patch.object(status, "fetch", side_effect=lambda p: status.hashicorp_rss(rss(), p))


def events():
    return db.session.scalars(db.select(NotificationEvent).order_by(NotificationEvent.created_at)).all()


def deliveries():
    return db.session.scalars(db.select(NotificationDelivery).order_by(NotificationDelivery.id)).all()


def test_initial_disruption_restart_dedup_new_incident_and_recovery(configured):
    status.poll_once()
    db.session.remove()  # no process-local dedup state
    status.poll_once()
    assert len(events()) == 1
    assert len(deliveries()) == 2
    configured.side_effect = lambda p: status.hashicorp_rss(rss(identity="two"), p)
    status.poll_once()
    assert len(events()) == 2
    configured.side_effect = TimeoutError
    status.poll_once()
    configured.side_effect = lambda p: status.hashicorp_rss(b"<rss><channel/></rss>", p)
    status.poll_once()
    assert len(events()) == 2
    configured.side_effect = lambda p: dict(reported_status="no_incidents", incidents=[], affected_components=[])
    status.poll_once()
    status.poll_once()
    assert [e.event_type for e in events()] == ["provider.disruption_started"] * 2 + ["provider.disruption_resolved"]


def test_existing_disruption_when_notifications_enabled(configured):
    db.session.add(ServiceStatusSnapshot(provider="terraform_cloud", snapshot={"reported_status": "disruption"}))
    db.session.commit()
    status.poll_once()
    assert len(events()) == 1


def test_state_and_event_rollback_together(configured, mocker):
    commit = mocker.patch.object(db.session, "commit", side_effect=RuntimeError)
    status.poll_once()
    mocker.stop(commit)
    assert not events()
    assert not deliveries()
    assert db.session.get(ServiceStatusSnapshot, "terraform_cloud") is None
    status.poll_once()
    assert len(events()) == 1


def test_no_destinations_or_initial_healthy_no_notifications(app, mocker):
    mocker.patch.object(status, "providers", return_value=[status.DEFAULT_PROVIDERS[0]])
    fetch = mocker.patch.object(status, "fetch", return_value=dict(reported_status="disruption", incidents=[]))
    status.poll_once()
    assert not events()
    mocker.patch.object(notify, "destinations", return_value=TARGETS)
    fetch.return_value = dict(reported_status="no_incidents", incidents=[])
    status.poll_once()
    assert not events()


def test_independent_retry_and_restart(configured, mocker):
    status.poll_once()
    clock = mocker.patch.object(notify.time, "time", return_value=2000000000)
    send = mocker.patch.object(notify, "send", side_effect=[HTTPError("secret", 429, "secret", {"Retry-After": "120"}, None), None])
    notify.deliver_once()
    first, second = deliveries()
    assert (first.state, first.attempts, first.last_error) == ("pending", 1, "HTTP 429")
    assert first.next_attempt_at == clock.return_value + 120
    assert second.state == "delivered"
    send.reset_mock(side_effect=True)
    notify.deliver_once()
    send.assert_not_called()
    db.session.remove()
    clock.return_value += 120
    notify.deliver_once()
    assert send.call_count == 1
    assert all(d.state == "delivered" for d in deliveries())


def test_permanent_failure_and_secret_redaction(configured, mocker):
    status.poll_once()
    mocker.patch.object(notify.time, "time", return_value=2000000000)
    mocker.patch.object(notify, "send", side_effect=[HTTPError("secret", 403, "secret", {}, None), TimeoutError("secret")])
    notify.deliver_once()
    first, second = deliveries()
    assert (first.state, first.last_error) == ("failed", "HTTP 403")
    assert (second.state, second.last_error) == ("pending", "TimeoutError")


def test_payloads(configured, mocker):
    status.poll_once()
    event = events()[0]
    opener = mocker.patch.object(notify, "build_opener").return_value
    opener.open.return_value.__enter__.return_value.status = 200
    notify.send(event, TARGETS[1])
    request = opener.open.call_args.args[0]
    assert json.loads(request.data) == notify.envelope(event)
    assert request.get_header("Authorization") == "Bearer secret"
    assert request.get_header("X-mc-hub-event-id") == event.id
    notify.send(event, TARGETS[0])
    body = json.loads(opener.open.call_args.args[0].data)
    assert body["blocks"][0]["text"]["type"] == "plain_text"
    assert "Delayed runs" in body["blocks"][0]["text"]["text"]
    assert notify.NoRedirect().redirect_request(None, None, 302, "", {}, "http://example.com") is None


def test_configuration():
    base = dict(auth_type=["NONE"], cors_allowed_origins=[], magic_castle_version_range=">= 13.0.0")
    schema = ConfigurationSchema()
    assert schema.load(base)["notification_destinations"] == []
    assert len(schema.load({**base, "notification_destinations": TARGETS})["notification_destinations"]) == 2
    for targets in ([TARGETS[0]] * 2, [{**TARGETS[0], "url": "http://example.com"}],
                    [{**TARGETS[0], "type": "unknown"}], [{**TARGETS[0], "token": "bad\nheader"}]):
        with pytest.raises(ValidationError):
            schema.load({**base, "notification_destinations": targets})


def test_migration_roundtrip():
    old = importlib.import_module("migrations.versions.0019_service_status")
    migration = importlib.import_module("migrations.versions.0020_notification_outbox")
    with create_engine("sqlite://").begin() as connection:
        with Operations.context(MigrationContext.configure(connection)):
            old.upgrade()
            migration.upgrade()
            assert "notification_delivery" in inspect(connection).get_table_names()
            migration.downgrade()
            assert "notification_event" not in inspect(connection).get_table_names()
            assert "notification_snapshot" not in [c["name"] for c in inspect(connection).get_columns("service_status_snapshot")]


def test_retry_preserves_order_and_disabled_destination_pauses(configured, mocker):
    status.poll_once()
    configured.side_effect = lambda p: dict(reported_status="no_incidents", incidents=[], affected_components=[])
    status.poll_once()
    clock = mocker.patch.object(notify.time, "time", return_value=2000000000)
    send = mocker.patch.object(notify, "send", side_effect=[TimeoutError, None, None])
    notify.deliver_once()
    assert [(call.args[1]["id"], call.args[0].event_type) for call in send.call_args_list] == [
        ("ops", "provider.disruption_started"),
        ("automation", "provider.disruption_started"),
        ("automation", "provider.disruption_resolved")]
    send.reset_mock(side_effect=True)
    targets = mocker.patch.object(notify, "destinations", return_value=[TARGETS[1]])
    clock.return_value += 120
    notify.deliver_once()
    send.assert_not_called()
    targets.return_value = TARGETS
    notify.deliver_once()
    assert [call.args[0].event_type for call in send.call_args_list] == [
        "provider.disruption_started", "provider.disruption_resolved"]
    assert all(d.state == "delivered" for d in deliveries())


def test_retry_after_http_date_and_invalid_values():
    assert notify.retry_after({"Retry-After": "Thu, 01 Jan 1970 00:02:00 GMT"}, 60) == 60
    assert notify.retry_after({"Retry-After": "invalid"}, 60) == 0
