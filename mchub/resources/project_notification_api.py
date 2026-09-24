from urllib.parse import urlsplit
import uuid

from flask import request
from marshmallow import ValidationError

from .api_view import ApiView
from ..configuration import NotificationDestinationSchema
from ..database import db
from ..exceptions.invalid_usage_exception import InvalidUsageException
from ..models.cloud.project import Project
from ..models.user import User
from ..models.notification import ProjectNotificationDestination, NotificationDelivery


def can_manage_notifications(user, project):
    return isinstance(user, User) and user.is_admin and user.is_project_admin(project)


def authorize(user, project_id):
    project = db.session.get(Project, project_id)
    if project is None or project not in user.projects or not can_manage_notifications(user, project):
        raise InvalidUsageException("Only hub operators who administer this project can manage its notifications.", status_code=403)
    return project


def retire_deliveries(destination):
    db.session.execute(db.update(NotificationDelivery).where(
        NotificationDelivery.destination_id == destination.delivery_id,
        NotificationDelivery.state == "pending").values(state="cancelled"))


def serialize(destination):
    if destination is None:
        return {"configured": False}
    last = db.session.scalar(db.select(NotificationDelivery).where(
        NotificationDelivery.destination_id == destination.delivery_id).order_by(NotificationDelivery.id.desc()).limit(1))
    return {"configured": True, "type": destination.type, "enabled": destination.enabled,
            "has_url": True, "has_token": bool(destination.token),
            "last_delivery": {"state": last.state, "attempts": last.attempts, "error": last.last_error,
                              "delivered_at": last.delivered_at} if last else None}


class ProjectNotificationAPI(ApiView):
    def get(self, user, project_id):
        authorize(user, project_id)
        return serialize(db.session.get(ProjectNotificationDestination, project_id))

    def put(self, user, project_id):
        authorize(user, project_id)
        data = request.get_json()
        if not isinstance(data, dict) or set(data) - {"type", "url", "token", "enabled"}:
            raise InvalidUsageException("Provide a notification type, HTTPS URL, optional token, and enabled flag.")
        current = db.session.get(ProjectNotificationDestination, project_id)
        kind = data.get("type", current.type if current else "webhook")
        url = data.get("url", current.url if current else None)
        token = data.get("token", current.token if current else "")
        enabled = data.get("enabled", current.enabled if current else True)
        try:
            if not isinstance(url, str) or not isinstance(token, str) or type(enabled) is not bool:
                raise ValueError
            if len(url) > 4096 or len(token) > 4096 or any(ord(c) < 32 for c in url + token):
                raise ValueError
            parts = urlsplit(url)
            if parts.username or parts.password or parts.fragment:
                raise ValueError
            NotificationDestinationSchema().load({"id": "project", "type": kind, "url": url,
                                                   "enabled": enabled, **({"token": token} if token else {})})
        except (ValidationError, TypeError, ValueError):
            raise InvalidUsageException("Use Slack or webhook, a valid HTTPS URL without credentials or fragment, and a valid token.")
        if current is not None and (current.type, current.url, current.token, current.enabled) == (kind, url, token, enabled):
            return serialize(current)
        if current is None:
            current = ProjectNotificationDestination(project_id=project_id)
            db.session.add(current)
        else:
            retire_deliveries(current)
        # A new routing identity prevents old pending events reaching a replacement URL.
        current.delivery_id = "project:" + str(uuid.uuid4())
        current.type, current.url, current.token, current.enabled = kind, url, token, enabled
        db.session.commit()
        return serialize(current)

    def delete(self, user, project_id):
        authorize(user, project_id)
        current = db.session.get(ProjectNotificationDestination, project_id)
        if current is not None:
            retire_deliveries(current)
            db.session.delete(current)
            db.session.commit()
        return {"configured": False}
