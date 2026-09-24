"""Live quota checks for plans starting within 24 hours; one alert per project/change."""
from collections import Counter
import hashlib
import json
import logging
import time

from ..database import db
from ..models.capacity_plan import CapacityPlan, CapacityQuotaCheck
from ..models.cloud.project import Project
from ..models.cloud.cloud_manager import CloudManager
from ..models.magic_castle.magic_castle import MagicCastleORM
from ..models.magic_castle.cluster_status_code import ClusterStatusCode as Status
from .capacity import budget, iso
from . import notifications

logger = logging.getLogger(__name__)
LOOKAHEAD = 24 * 3600
CHECK_INTERVAL = 3600
RETRY_INTERVAL = 15 * 60


def signature(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def inputs(project_id, now):
    plans = list(db.session.scalars(db.select(CapacityPlan).where(
        CapacityPlan.project_id == project_id, CapacityPlan.ends_at > now,
        CapacityPlan.status.not_in(["cancelled", "ended"])).order_by(CapacityPlan.id)))
    deployed = set(db.session.scalars(db.select(MagicCastleORM.usage_id).where(
        MagicCastleORM.project_id == project_id, MagicCastleORM.undeployed.is_(False),
        MagicCastleORM.status.in_([Status.PROVISIONING_RUNNING, Status.PROVISIONING_SUCCESS, Status.PROVISIONING_ERROR]))))
    targets = [p for p in plans if now < p.starts_at <= now + LOOKAHEAD]
    snapshot = [{"id": p.id, "starts_at": p.starts_at, "ends_at": p.ends_at,
                 "name": p.definition.get("cluster_name", ""), "demand": p.demand,
                 "status": p.status, "cluster_usage_id": p.cluster_usage_id} for p in plans]
    return plans, targets, deployed, signature({"plans": snapshot, "targets": [p.id for p in targets],
                                               "deployed": sorted(deployed)})


def evaluate(plans, targets, deployed, available):
    """Check concurrent additional demand at each upcoming start, not the sum of disjoint plans."""
    checks = []
    for starts_at in sorted({p.starts_at for p in targets}):
        active = [p for p in plans if p.starts_at <= starts_at < p.ends_at]
        demand = Counter()
        for plan in active:
            if plan.cluster_usage_id not in deployed:
                demand.update(plan.demand)
        shortages = {key: value - available[key] for key, value in demand.items()
                     if available.get(key) is not None and value > available[key]}
        checks.append({"starts_at": iso(starts_at), "plan_ids": [p.id for p in active],
                       "required": dict(demand), "shortages": shortages})
    return checks


def check_project(project_id, now=None):
    now = time.time() if now is None else now
    project = db.session.get(Project, project_id)
    if project is None:
        return
    plans, targets, deployed, fingerprint = inputs(project_id, now)
    targets_config = notifications.project_destinations(project_id)
    fingerprint = signature({"inputs": fingerprint, "destinations": [d["id"] for d in targets_config]})
    row = db.session.get(CapacityQuotaCheck, project_id)
    if row is not None and row.input_signature == fingerprint and row.next_check_at > now:
        return
    payload = {"project_id": project_id, "project_name": project.name, "checked_at": iso(now),
               "plans": [{"id": p.id, "name": p.definition.get("cluster_name", ""),
                          "starts_at": iso(p.starts_at), "ends_at": iso(p.ends_at)} for p in targets],
               "status": "no_upcoming_plans", "checks": [],
               "notifications_enabled": bool(targets_config)}
    if targets:
        try:
            available = budget(project, CloudManager(project).manager)
            checks = evaluate(plans, targets, deployed, available)
            payload.update(available=available, checks=checks,
                           status="insufficient" if any(c["shortages"] for c in checks) else "sufficient")
        except Exception:
            # Do not expose cloud credentials or provider exception bodies.
            logger.warning("Could not check live quota for project %s", project_id)
            payload["status"] = "unknown"
    # Re-read after cloud I/O: do not persist or notify a cancelled/edited plan snapshot.
    db.session.rollback()
    if db.session.get(Project, project_id) is None:
        return
    current_fingerprint = signature({"inputs": inputs(project_id, time.time())[3],
                                     "destinations": [d["id"] for d in notifications.project_destinations(project_id)]})
    if current_fingerprint != fingerprint:
        db.session.rollback()
        return
    row = db.session.get(CapacityQuotaCheck, project_id)
    if row is None:
        row = CapacityQuotaCheck(project_id=project_id)
        db.session.add(row)
    row.checked_at = now
    row.next_check_at = now + (RETRY_INTERVAL if payload["status"] == "unknown" else CHECK_INTERVAL)
    row.input_signature = fingerprint
    row.result = payload
    if payload["status"] == "insufficient":
        # checked_at changes hourly; exclude it from deduplication.
        alert_signature = signature({"plans": payload["plans"], "checks": payload["checks"],
                                     "destinations": [d["id"] for d in targets_config]})
        if targets_config and row.notification_signature != alert_signature:
            lines = [f'{project.name}: insufficient available quota for plans starting within 24 hours.']
            lines.extend(f'{p["name"]} starts {p["starts_at"]}' for p in payload["plans"])
            for check in payload["checks"]:
                if check["shortages"]:
                    short = ", ".join(f'{"RAM (GiB)" if key == "ram" else key}: {value / 1024 if key == "ram" else value:g}'
                                      for key, value in check["shortages"].items())
                    lines.append(f'{check["starts_at"]}: short by {short}.')
            lines.append("Current usage is assumed to continue; review the project capacity planner.")
            notifications.enqueue("capacity.quota_insufficient", str(project_id),
                                  {**payload, "summary": "\n".join(lines)}, targets_config)
            row.notification_signature = alert_signature
    elif payload["status"] != "unknown":
        row.notification_signature = None
    db.session.commit()


def poll_once():
    now = time.time()
    project_ids = set(db.session.scalars(db.select(CapacityPlan.project_id).where(
        CapacityPlan.status.not_in(["cancelled", "ended"]), CapacityPlan.starts_at > now,
        CapacityPlan.starts_at <= now + LOOKAHEAD)))
    # Clear stale warnings when the last target started, was cancelled, or moved.
    project_ids.update(db.session.scalars(db.select(CapacityQuotaCheck.project_id)))
    for project_id in sorted(project_ids):
        try:
            check_project(project_id, now)
        except Exception:
            db.session.rollback()
            logger.exception("Capacity preflight failed for project %s", project_id)
        finally:
            db.session.remove()
