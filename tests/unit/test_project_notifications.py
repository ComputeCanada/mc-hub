import importlib
import time

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text

from mchub.database import db
from mchub.models.user import User, TokenSuperUser
from mchub.models.notification import ProjectNotificationDestination, NotificationDelivery, NotificationEvent
from mchub.models.cloud.project import Project
from mchub.resources.project_notification_api import ProjectNotificationAPI, can_manage_notifications
from mchub.exceptions.invalid_usage_exception import InvalidUsageException
from mchub.services import notifications, capacity_preflight
from tests.unit.test_capacity import app, cluster, config_mock, plan  # noqa: F401


@pytest.fixture
def operator(plan, mocker):
    plan.project.admins.append(plan.owner)
    db.session.commit()
    mocker.patch("mchub.models.user.get_config", return_value={"admins": [plan.owner.scoped_id]})
    return User(plan.owner, "owner", "example.org", "saml")


def put(app, user, project_id, payload):
    with app.test_request_context(json=payload):
        return ProjectNotificationAPI().put(user, project_id)


@pytest.mark.parametrize("hub_operator,project_admin", [(False, False), (True, False), (False, True), (True, True)])
def test_requires_both_hub_operator_and_project_admin(plan, app, mocker, hub_operator, project_admin):
    if project_admin:
        plan.project.admins.append(plan.owner); db.session.commit()
    mocker.patch("mchub.models.user.get_config", return_value={"admins": [plan.owner.scoped_id] if hub_operator else []})
    user = User(plan.owner, "owner", "example.org", "saml")
    assert can_manage_notifications(user, plan.project) == (hub_operator and project_admin)
    if hub_operator and project_admin:
        assert put(app, user, plan.project_id, {"type": "webhook", "url": "https://example.com/secret"})["configured"]
    else:
        for operation in (lambda: ProjectNotificationAPI().get(user, plan.project_id),
                          lambda: put(app, user, plan.project_id, {"type": "webhook", "url": "https://example.com/secret"}),
                          lambda: ProjectNotificationAPI().delete(user, plan.project_id)):
            with pytest.raises(InvalidUsageException) as error:
                operation()
            assert error.value.status_code == 403


def test_service_token_cannot_manage_hooks(plan, app):
    with pytest.raises(InvalidUsageException) as error:
        put(app, TokenSuperUser(), plan.project_id, {"url": "https://example.com/hook"})
    assert error.value.status_code == 403


def test_operator_cannot_manage_another_project(operator, app):
    other = Project(name="Other", provider="openstack", github_template="x", tfcloud_project_id="other")
    db.session.add(other); db.session.commit()
    with pytest.raises(InvalidUsageException):
        put(app, operator, other.id, {"url": "https://example.com/hook"})


def test_secrets_write_only_and_omitted_values_preserved(operator, plan, app):
    result = put(app, operator, plan.project_id, {"type": "webhook", "url": "https://example.com/url-secret", "token": "token-secret"})
    assert result["has_url"] and result["has_token"]
    assert "url-secret" not in str(result) and "token-secret" not in str(result)
    result = ProjectNotificationAPI().get(operator, plan.project_id)
    assert "url" not in result and "token" not in result
    put(app, operator, plan.project_id, {"enabled": False})
    saved = db.session.get(ProjectNotificationDestination, plan.project_id)
    assert saved.url == "https://example.com/url-secret" and saved.token == "token-secret"
    put(app, operator, plan.project_id, {"token": ""})
    assert saved.token == ""


@pytest.mark.parametrize("payload", [
    {"url": "http://example.com/hook"}, {"url": "https://user:password@example.com/hook"},
    {"url": "https://example.com/hook#secret"}, {"url": "https://example.com/\nsecret"},
    {"url": "https://example.com/hook", "token": "secret\r\nX-Injected: true"},
    {"url": "https://example.com/hook", "type": "email"},
    {"url": "https://example.com/hook", "enabled": "false"},
])
def test_invalid_settings_rejected_without_persisting(operator, plan, app, payload):
    with pytest.raises(InvalidUsageException):
        put(app, operator, plan.project_id, payload)
    assert db.session.get(ProjectNotificationDestination, plan.project_id) is None


def test_replacing_disabling_and_removing_destination_cancels_pending(operator, plan, app):
    put(app, operator, plan.project_id, {"url": "https://example.com/first"})
    old = notifications.project_destinations(plan.project_id)[0]
    notifications.enqueue("capacity.quota_insufficient", str(plan.project_id), {}, [old]); db.session.commit()
    put(app, operator, plan.project_id, {"url": "https://example.com/second"})
    assert db.session.scalar(db.select(NotificationDelivery)).state == "cancelled"
    current = notifications.project_destinations(plan.project_id)[0]
    assert old["id"] != current["id"]
    notifications.enqueue("capacity.quota_insufficient", str(plan.project_id), {}, [current]); db.session.commit()
    put(app, operator, plan.project_id, {"enabled": False})
    assert notifications.project_destinations(plan.project_id) == []
    assert all(d.state == "cancelled" for d in db.session.scalars(db.select(NotificationDelivery)))
    ProjectNotificationAPI().delete(operator, plan.project_id)
    assert ProjectNotificationAPI().get(operator, plan.project_id) == {"configured": False}


def test_capacity_routes_only_to_matching_project_and_provider_to_global(operator, plan, app, mocker):
    put(app, operator, plan.project_id, {"url": "https://example.com/project"})
    target = notifications.project_destinations(plan.project_id)[0]
    global_target = {"id": "global", "type": "webhook", "url": "https://example.com/global"}
    mocker.patch.object(notifications, "destinations", return_value=[global_target])
    notifications.enqueue("capacity.quota_insufficient", str(plan.project_id), {}, [target, global_target])
    notifications.enqueue("capacity.quota_insufficient", "another-project", {}, [target])
    notifications.enqueue("provider.disruption_started", "provider", {}, [global_target, target])
    db.session.commit()
    send = mocker.patch.object(notifications, "send")
    notifications.deliver_once()
    assert {(call.args[0].event_type, call.args[1]["id"]) for call in send.call_args_list} == {
        ("capacity.quota_insufficient", target["id"]), ("provider.disruption_started", "global")}
    assert send.call_count == 2
    assert sum(d.state == "cancelled" for d in db.session.scalars(db.select(NotificationDelivery))) == 3


def test_new_project_hook_gets_existing_warning_without_waiting_an_hour(operator, plan, app, mocker):
    plan.starts_at = time.time() + 3600; plan.ends_at = plan.starts_at + 3600; db.session.commit()
    mocker.patch.object(capacity_preflight, "CloudManager")
    mocker.patch.object(capacity_preflight, "budget", return_value={"vcpus": 1})
    mocker.patch.object(notifications, "destinations", return_value=[{"id": "global"}])
    capacity_preflight.check_project(plan.project_id)
    assert db.session.scalar(db.select(NotificationEvent)) is None
    put(app, operator, plan.project_id, {"url": "https://example.com/project"})
    capacity_preflight.check_project(plan.project_id)
    delivery = db.session.scalar(db.select(NotificationDelivery))
    assert delivery.destination_id == notifications.project_destinations(plan.project_id)[0]["id"]


def test_migration_cancels_legacy_global_capacity_alerts():
    migration = importlib.import_module("migrations.versions.0023_project_notifications")
    with create_engine("sqlite://").begin() as connection:
        connection.execute(text("CREATE TABLE notification_event (id TEXT, event_type TEXT)"))
        connection.execute(text("CREATE TABLE notification_delivery (event_id TEXT, state TEXT)"))
        connection.execute(text("INSERT INTO notification_event VALUES ('1', 'capacity.quota_insufficient'), ('2', 'provider.disruption_started')"))
        connection.execute(text("INSERT INTO notification_delivery VALUES ('1', 'pending'), ('2', 'pending')"))
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
            assert "project_notification_destination" in inspect(connection).get_table_names()
            assert list(connection.execute(text("SELECT state FROM notification_delivery ORDER BY event_id")).scalars()) == ["cancelled", "pending"]
            migration.downgrade()
            assert "project_notification_destination" not in inspect(connection).get_table_names()


def test_http_settings_and_project_permission_flag(operator, plan, app):
    # Check the real authentication decorators and route registration as well.
    plan.project.env = {}; db.session.commit()
    headers = {"eduPersonPrincipalName": plan.owner.scoped_id, "givenName": "Owner",
               "surname": "Example", "mail": plan.owner.scoped_id}
    client = app.test_client()
    response = client.get(f"/api/projects/{plan.project_id}", headers=headers)
    assert response.status_code == 200
    assert response.json["can_manage_notifications"] is True
    response = client.put(f"/api/projects/{plan.project_id}/notification-destination", headers=headers,
                          json={"type": "slack", "url": "https://hooks.slack.com/services/secret"})
    assert response.status_code == 200 and response.json["configured"]
    assert "secret" not in response.get_data(as_text=True)
    plan.project.admins.clear(); db.session.commit()
    response = client.get(f"/api/projects/{plan.project_id}/notification-destination", headers=headers)
    assert response.status_code == 403
    response = client.get(f"/api/projects/{plan.project_id}", headers=headers)
    assert response.json["can_manage_notifications"] is False
