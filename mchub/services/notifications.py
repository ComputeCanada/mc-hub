"""Transactional event creation and destination adapters. Never commit in enqueue()."""
import json
import time
import uuid
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from ..configuration import get_config
from ..database import db
from ..models.notification import NotificationDelivery, NotificationEvent


def destinations():
    return [d for d in get_config().get("notification_destinations", []) if d.get("enabled", True)]


def enqueue(event_type, resource_id, payload, targets):
    """Caller commits this event together with its business-state change."""
    event = NotificationEvent(id=str(uuid.uuid4()), event_type=event_type,
                              resource_id=resource_id, created_at=time.time(), payload=payload)
    db.session.add(event)
    for target in targets:
        db.session.add(NotificationDelivery(event=event, destination_id=target["id"],
                                            next_attempt_at=event.created_at))
    return event


def provider_events(row, provider, snapshot):
    targets = destinations()
    if not targets:
        return
    previous = row.notification_snapshot or {}
    disrupted = snapshot["reported_status"] == "disruption"
    old_ids = {i["id"] for i in previous.get("incidents", [])}
    new_incidents = [i for i in snapshot.get("incidents", [])
                     if i["id"] not in old_ids and i.get("confirmed", True)]
    event_type = None
    if disrupted and (previous.get("reported_status") != "disruption" or new_incidents):
        event_type = "provider.disruption_started"
    elif snapshot["reported_status"] == "no_incidents" and previous.get("reported_status") == "disruption":
        event_type = "provider.disruption_resolved"
    if event_type:
        enqueue(event_type, provider["id"], {
            "provider": provider["id"], "name": provider["name"], "status_url": provider["status_url"],
            "reported_status": snapshot["reported_status"],
            "affected_components": snapshot.get("affected_components", []),
            "incidents": snapshot.get("incidents", []),
        }, targets)
    row.notification_snapshot = snapshot


class NoRedirect(HTTPRedirectHandler):
    # Webhook URLs and authorization must not be forwarded to another endpoint.
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def envelope(event):
    return {"version": 1, "id": event.id, "type": event.event_type,
            "resource_id": event.resource_id,
            "occurred_at": datetime.fromtimestamp(event.created_at, timezone.utc).isoformat(),
            "data": event.payload}


def send(event, destination):
    body = envelope(event)
    if destination["type"] == "slack":
        data = event.payload
        if event.event_type in {"provider.disruption_started", "provider.disruption_resolved"}:
            state = "reports a service disruption" if event.event_type.endswith("started") else "service restored"
            lines = [f'{data["name"]}: {state}', data["status_url"]]
            lines.extend(f'{i["title"]} — {i["status"]}' +
                         (" (current status unconfirmed)" if not i.get("confirmed", True) else "")
                         for i in data.get("incidents", []))
        else:
            lines = [f"{event.event_type}: {event.resource_id}", str(data.get("summary", ""))]
        lines.append(body["occurred_at"])
        # Plain text prevents provider-controlled titles from triggering mentions.
        body = {"blocks": [{"type": "section", "text": {"type": "plain_text", "text": "\n".join(lines)[:3000]}}]}
    headers = {"Content-Type": "application/json", "User-Agent": "MC-Hub notifications",
               "X-MC-Hub-Event-ID": event.id}
    if destination.get("token"):
        headers["Authorization"] = "Bearer " + destination["token"]
    request = Request(destination["url"], data=json.dumps(body).encode(), headers=headers, method="POST")
    with build_opener(NoRedirect()).open(request, timeout=10) as response:
        if not 200 <= response.status < 300:
            raise HTTPError(destination["url"], response.status, "Unexpected status", response.headers, None)


def retry_after(headers, now):
    value = headers.get("Retry-After", "") if headers else ""
    try:
        return max(0, float(value))
    except ValueError:
        try:
            return max(0, parsedate_to_datetime(value).timestamp() - now)
        except (ValueError, TypeError, OverflowError):
            return 0


def deliver_once():
    """Single supervised consumer; pending rows survive crashes during HTTP delivery."""
    configured = {d["id"]: d for d in destinations()}
    if not configured:
        return
    for destination in configured.values():
        _deliver_destination(destination)


def _deliver_destination(destination):
    # Preserve event order per destination, including across delayed retries.
    ids = db.session.scalars(db.select(NotificationDelivery.id).where(
        NotificationDelivery.state == "pending",
        NotificationDelivery.destination_id == destination["id"]
    ).order_by(NotificationDelivery.id).limit(50)).all()
    db.session.remove()
    for identity in ids:
        delivery = db.session.get(NotificationDelivery, identity)
        if delivery.next_attempt_at > time.time():
            db.session.remove()
            break
        event = delivery.event
        db.session.expunge(event)
        db.session.expunge(delivery)
        # Close the read transaction before network I/O, especially on SQLite.
        db.session.remove()
        delay, error, permanent = 0, None, False
        try:
            send(event, destination)
        except HTTPError as exc:
            error = f"HTTP {exc.code}"
            permanent = exc.code not in (408, 429) and exc.code < 500
            delay = retry_after(exc.headers, time.time())
            exc.close()
        except Exception as exc:
            # Exception strings can contain secret webhook URLs or response bodies.
            error = type(exc).__name__
        delivery = db.session.get(NotificationDelivery, identity)
        delivery.attempts += 1
        delivery.last_error = error
        if error:
            delivery.state = "failed" if permanent else "pending"
            delivery.next_attempt_at = time.time() + max(delay, min(3600, 5 * 2 ** min(delivery.attempts, 10)))
        else:
            delivery.state = "delivered"
            delivery.delivered_at = time.time()
        db.session.commit()
        db.session.remove()
        if error and not permanent:
            break
