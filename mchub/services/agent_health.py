"""Shared agent health snapshots and transactional operator notifications."""
import logging
import time

from ..configuration import get_config
from ..database import db
from ..models.agent_health import AgentHealthSnapshot
from .terraform_cloud_api import configured_agent_pool, get_terraform_cloud
from . import notifications

logger = logging.getLogger(__name__)
HEALTHY_INTERVAL = 300
RECOVERY_INTERVAL = 30
STALE_SECONDS = 660


def read_availability(project):
    """Read-only: browser requests never trigger Terraform Cloud health checks."""
    pool = configured_agent_pool(project)
    if not pool:
        return {"available": True, "message": ""}
    row = db.session.get(AgentHealthSnapshot, (get_config()["tfcloud_organization"], pool))
    if row is None or time.time() - row.checked_at > STALE_SECONDS:
        return {"available": False, "message":
                "Terraform agent status is unavailable or out of date. Waiting for the background health check."}
    return {"available": row.status == "healthy", "message": row.message}


def poll_once():
    config = get_config()
    organization = config["tfcloud_organization"]
    pools = {c["agent_pool_name"] for c in config.get("openstack_clouds", []) if c.get("agent_pool_name")}
    for pool in sorted(pools):
        try:
            row = db.session.get(AgentHealthSnapshot, (organization, pool))
            interval = HEALTHY_INTERVAL if row and row.status == "healthy" else RECOVERY_INTERVAL
            if row and time.time() - row.checked_at < interval:
                continue
            # Do not hold a database transaction during network I/O.
            db.session.remove()
            result = get_terraform_cloud().check_agent_pool(pool)
            row = db.session.get(AgentHealthSnapshot, (organization, pool))
            if row is None:
                row = AgentHealthSnapshot(organization=organization, pool_name=pool)
                db.session.add(row)
            row.checked_at = time.time()
            row.status, row.message = result["status"], result["message"]
            targets = notifications.destinations()
            if targets and row.notified_status != row.status:
                event_type = {
                    "unavailable": "agent_pool.unavailable",
                    "unknown": "agent_pool.check_failed",
                    "healthy": "agent_pool.recovered",
                }[row.status]
                # Initial healthy observations don't need an operator alert.
                if row.status != "healthy" or row.notified_status is not None:
                    summary = row.message or "Terraform Cloud agents are available again."
                    notifications.enqueue(event_type, f"{organization}/{pool}", {
                        "organization": organization, "pool_name": pool,
                        "status": row.status, "summary": summary,
                    }, targets)
                row.notified_status = row.status
            db.session.commit()
        except Exception:
            db.session.rollback()
            logger.exception("Could not update agent health for pool %s", pool)
        finally:
            db.session.remove()
