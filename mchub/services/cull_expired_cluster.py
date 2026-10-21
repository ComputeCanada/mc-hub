"""Clean up expired clusters and ended capacity plans through one lifecycle path."""
import logging
import time
from datetime import datetime

from .. import create_app
from ..database import db
from ..exceptions.invalid_usage_exception import BusyClusterException, InvalidUsageException
from ..models.magic_castle.magic_castle import MagicCastle, MagicCastleORM
from ..models.capacity_plan import CapacityPlan
from ..models.magic_castle.cluster_status_code import ClusterStatusCode as Status
from ..models.magic_castle.terraform_cloud_status import TFCloudStatusCode
from . import cluster_lifecycle as lifecycle
from . import agent_health, service_status
from .terraform_cloud_api import get_terraform_cloud
from .worker_logging import configure_worker_logging

logger = logging.getLogger(__name__)
SWEEP_INTERVAL = 300
PLAN_WAIT_TIMEOUT = 5 * 60
CAPACITY_CLEANUP_STATES = ("started", "manual_ready", "manual_starting", "failed", "cleanup_pending", "cleanup_failed")


def is_expired(orm, now):
    return (not orm.undeployed and orm.expiration_date is not None
            and datetime.strptime(orm.expiration_date, "%Y-%m-%d") < now)


class ExpirationDeferred(Exception):
    """Dependencies are unavailable; keep the cluster eligible for retry."""


def ensure_expiration_ready(orm):
    # Disabled provider monitors are intentionally absent from read_status().
    for provider in service_status.read_status()["providers"]:
        if provider["provider"] not in {"github", "terraform_cloud"}:
            continue
        if provider["reported_status"] == "disruption":
            raise ExpirationDeferred(f'{provider["name"]} reports a service disruption')
        if (provider["freshness"] != "fresh" or provider["last_attempt_ok"] is not True
                or provider["reported_status"] != "no_incidents"):
            raise ExpirationDeferred(f'{provider["name"]} health cannot currently be verified')
    availability = agent_health.read_availability(orm.project)
    if not availability["available"]:
        raise ExpirationDeferred(availability["message"])
    # Keep the live agent guard as well: a healthy snapshot can become outdated
    # before the next monitor sweep. Projects without a pool skip remote calls.
    try:
        get_terraform_cloud().ensure_agent_available(orm.project)
    except InvalidUsageException as error:
        if error.status_code != 503:
            raise
        raise ExpirationDeferred(error.message) from None


def expire_cluster(orm, now):
    if is_expired(orm, now):
        cleanup_cluster(orm, lambda current: is_expired(current, datetime.now()))


def cleanup_cluster(orm, is_due):
    """One teardown path for dated expiration and capacity period deadlines."""
    if not is_due(orm):
        return
    # Gate before status refresh: even refresh can issue recovery API mutations.
    ensure_expiration_ready(orm)
    # Refresh remote progress before deciding whether the cluster is busy/empty.
    cluster = MagicCastle(orm)
    cluster.status
    if not is_due(orm):
        return
    if cluster.is_busy or orm.status == Status.BACKGROUND_TASK_RUNNING:
        raise BusyClusterException
    if orm.undeployed:
        return
    hostname = orm.hostname
    resume_destroy = False
    if orm.status == Status.CREATED and orm.tfcloud_run.run_id:
        remote_status, is_destroy = get_terraform_cloud().get_run_status(orm.tfcloud_run.run_id)
        resume_destroy = is_destroy and remote_status in {
            TFCloudStatusCode.PLANNED, TFCloudStatusCode.PLANNED_AND_SAVED,
        }
        if is_destroy and not resume_destroy and remote_status not in {
            TFCloudStatusCode.ERRORED, TFCloudStatusCode.CANCELED,
            TFCloudStatusCode.FORCE_CANCELED, TFCloudStatusCode.DISCARDED,
        }:
            # Remote progress may have changed since cluster.status refreshed.
            # Observe it on the next sweep rather than replacing a live run.
            raise BusyClusterException
    if not resume_destroy:
        lifecycle.claim_background_task(orm, owner="expiration")
        logger.info("Cleaning up cluster %s", hostname)
        lifecycle.execute_claimed_task(hostname, lifecycle.plan_teardown, hostname, PLAN_WAIT_TIMEOUT)

    orm = lifecycle.get_cluster(hostname)
    if orm.undeployed or orm.status == Status.NOT_DEPLOYED:
        return
    # plan_destruction returns only after the destroy plan is available.
    run_id = orm.tfcloud_run.run_id
    lifecycle.validate_apply(orm)
    # A user can extend expiration while planning finishes. Recheck before apply.
    db.session.refresh(orm)
    if not is_due(orm):
        return
    ensure_expiration_ready(orm)
    # Health checks involve network I/O; fence expiration changes during them.
    db.session.refresh(orm)
    if not is_due(orm):
        return
    lifecycle.claim_background_task(orm, owner="expiration")
    lifecycle.execute_claimed_task(hostname, lifecycle.apply_cluster, hostname, None, run_id)


def end_capacity_plan(plan_id):
    """The persisted plan deadline is the durable request for cleanup."""
    claimed = db.session.execute(db.update(CapacityPlan).where(
        CapacityPlan.id == plan_id, CapacityPlan.ends_at <= time.time(),
        CapacityPlan.cluster_usage_id.is_not(None),
        CapacityPlan.status.in_(CAPACITY_CLEANUP_STATES),
    ).values(status="ending"))
    db.session.commit()
    if claimed.rowcount != 1:
        return
    plan = db.session.get(CapacityPlan, plan_id)
    try:
        orm = db.session.scalar(db.select(MagicCastleORM).where(
            MagicCastleORM.usage_id == plan.cluster_usage_id,
            MagicCastleORM.project_id == plan.project_id,
        ))
        if orm is not None:
            def is_due(current):
                db.session.refresh(plan)
                return (plan.status == "ending" and plan.ends_at <= time.time()
                        and plan.cluster_usage_id == current.usage_id
                        and plan.project_id == current.project_id)

            cleanup_cluster(orm, is_due)
            db.session.refresh(plan)
            if plan.status != "ending":
                return
            if plan.ends_at > time.time():
                plan.status = "cleanup_pending"
                plan.message = "Cleanup deferred until the updated period ends."
            elif not orm.undeployed:
                plan.status = "cleanup_pending"
                plan.message = "Teardown requested; waiting for resources to be removed."
            else:
                plan.status = "ended"
                plan.message = "The period ended; cluster resources have been removed."
        else:
            plan.status = "ended"
            plan.message = "The period ended; the linked cluster no longer exists."
        db.session.commit()
    except (ExpirationDeferred, BusyClusterException) as error:
        db.session.rollback()
        plan = db.session.get(CapacityPlan, plan_id)
        plan.status = "cleanup_pending"
        reason = str(error) if isinstance(error, ExpirationDeferred) else "Waiting for the current cluster operation."
        plan.message = ("Cleanup deferred: " + reason)[:255]
        db.session.commit()
        logger.info("Capacity plan %s cleanup deferred: %s", plan_id, reason)
    except Exception:
        db.session.rollback()
        logger.exception("Capacity plan %s cleanup failed; retrying next sweep", plan_id)
        plan = db.session.get(CapacityPlan, plan_id)
        plan.status = "cleanup_failed"
        plan.message = "Cleanup failed; the cleanup worker will retry. Check cluster status."
        db.session.commit()


def poll_once():
    capacity_due = list(db.session.execute(db.select(CapacityPlan.id, CapacityPlan.cluster_usage_id).where(
        CapacityPlan.cluster_usage_id.is_not(None), CapacityPlan.ends_at <= time.time(),
        CapacityPlan.status.in_(CAPACITY_CLEANUP_STATES),
    )))
    for plan_id, _ in capacity_due:
        try:
            end_capacity_plan(plan_id)
        except Exception:
            db.session.rollback()
            logger.exception("Could not process capacity cleanup %s", plan_id)
        finally:
            db.session.remove()
    ids = list(db.session.scalars(db.select(MagicCastleORM.id).where(
        MagicCastleORM.benchmark_run_id.is_(None),
        MagicCastleORM.benchmark_id.is_(None),
        MagicCastleORM.usage_id.not_in([usage_id for _, usage_id in capacity_due]),
        MagicCastleORM.expiration_date.is_not(None), MagicCastleORM.undeployed.is_(False),
    )))
    for cluster_id in ids:
        try:
            orm = db.session.get(MagicCastleORM, cluster_id)
            if orm is not None and is_expired(orm, datetime.now()):
                expire_cluster(orm, datetime.now())
        except ExpirationDeferred as error:
            db.session.rollback()
            logger.info("Cluster %s expiration deferred: %s; retrying next sweep", cluster_id, error)
        except BusyClusterException:
            db.session.rollback()
            logger.info("Cluster %s is busy; expiration will retry next sweep", cluster_id)
        except Exception:
            db.session.rollback()
            logger.exception("Could not expire cluster %s", cluster_id)
        finally:
            db.session.remove()


def recover_interrupted_expiration():
    # The supervisor guarantees only one expiration process. Recover only its
    # claims, leaving operations owned by HTTP request workers alone.
    # Old capacity-worker cleanup claims are transferred on upgrade. New
    # capacity starts still use "capacity" and must not be recovered here.
    interrupted = list(db.session.scalars(db.select(CapacityPlan).where(CapacityPlan.status == "ending")))
    for plan in interrupted:
        orm = db.session.scalar(db.select(MagicCastleORM).where(MagicCastleORM.usage_id == plan.cluster_usage_id))
        if orm is not None and orm.creation_step == "capacity":
            if orm.status == Status.BACKGROUND_TASK_RUNNING:
                orm.status = Status.PLAN_RUNNING if orm.tfcloud_run.run_id else Status.PLAN_ERROR
            orm.creation_step = None
        plan.status = "cleanup_pending"
        plan.message = "Cleanup was interrupted; the cleanup worker will retry."
    for orm in db.session.scalars(db.select(MagicCastleORM).where(
        MagicCastleORM.creation_step == "expiration",
    )):
        if orm.status == Status.BACKGROUND_TASK_RUNNING:
            orm.status = Status.PLAN_RUNNING if orm.tfcloud_run.run_id else Status.PLAN_ERROR
        orm.creation_step = None
    db.session.commit()


def main(interval=SWEEP_INTERVAL):
    configure_worker_logging()
    app = create_app()
    with app.app_context():
        recover_interrupted_expiration()
    while True:
        with app.app_context():
            try:
                poll_once()
            except Exception:
                db.session.rollback()
                logger.exception("Cleanup sweep failed")
        time.sleep(interval)


if __name__ == "__main__":
    main()
