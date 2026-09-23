"""Start opted-in plans once, with durable claims and no automatic retries."""
import logging
import time
from copy import deepcopy

from .. import create_app
from ..database import db
from ..models.capacity_plan import CapacityPlan
from ..models.magic_castle.magic_castle import MagicCastle, MagicCastleORM
from ..models.magic_castle.cluster_status_code import ClusterStatusCode as Status
from ..models.usage import new_id
from ..models.user import User
from ..exceptions.invalid_usage_exception import InvalidUsageException, BusyClusterException
from . import cluster_lifecycle as lifecycle
from .capacity import resource_demand, budget
from ..models.cloud.cloud_manager import CloudManager
from ..models.cloud.aws_manager import ensure_aws_feasible
from .worker_logging import configure_worker_logging

logger = logging.getLogger(__name__)


def start_plan(plan_id):
    now = time.time()
    claimed = db.session.execute(db.update(CapacityPlan).where(
        CapacityPlan.id == plan_id, CapacityPlan.status == "planned",
        CapacityPlan.auto_create.is_(True), CapacityPlan.starts_at <= now,
        CapacityPlan.ends_at > now).values(status="starting"))
    db.session.commit()
    if claimed.rowcount != 1:
        return
    plan = db.session.get(CapacityPlan, plan_id)
    try:
        user = User(plan.owner, "", "", "scheduled")
        if plan.project not in user.projects:
            raise InvalidUsageException("The plan owner no longer has project access.")
        manager = CloudManager(plan.project).manager
        demand = resource_demand(plan.project, plan.definition, manager)
        available = budget(plan.project, manager)
        if any(available.get(k) is not None and v > available[k] for k, v in demand.items()):
            raise InvalidUsageException("Insufficient quota at the scheduled start.")
        ensure_aws_feasible(plan.project, plan.definition)
        cluster = MagicCastle()
        cluster.orm.usage_id = new_id()
        plan.cluster_usage_id = cluster.orm.usage_id
        db.session.commit()
        cluster.plan_creation(deepcopy(plan.definition), plan.owner_id, timeout=300)
        plan.cluster_usage_id = cluster.orm.usage_id
        db.session.commit()
        lifecycle.validate_apply(cluster.orm)
        # If setup overran the period, leave its plan for manual review.
        if time.time() >= plan.ends_at or plan.project not in user.projects:
            raise InvalidUsageException("The period ended or project access changed before apply.")
        ensure_aws_feasible(plan.project, cluster.config)
        lifecycle.claim_background_task(cluster.orm, owner="capacity")
        lifecycle.execute_claimed_task(cluster.hostname, lifecycle.apply_cluster, cluster.hostname, plan.owner.scoped_id)
        plan.status = "started"
        plan.message = "Creation requested. Check the cluster for deployment progress."
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception("Scheduled capacity plan %s failed", plan_id)
        plan = db.session.get(CapacityPlan, plan_id)
        plan.status = "failed"
        plan.message = "Automatic creation failed. Review the cluster and quota before creating manually."
        db.session.commit()


def recover_interrupted():
    interrupted = list(db.session.scalars(db.select(CapacityPlan).where(CapacityPlan.status == "starting")))
    for plan in interrupted:
        orm = db.session.scalar(db.select(MagicCastleORM).where(MagicCastleORM.usage_id == plan.cluster_usage_id)) if plan.cluster_usage_id else None
        if orm is not None and orm.status == Status.PLAN_RUNNING and not orm.tfcloud_run.run_id:
            orm.status = Status.PLAN_ERROR
            orm.creation_step = None
    db.session.execute(db.update(CapacityPlan).where(CapacityPlan.status == "starting").values(
        status="failed", message="Creation was interrupted. Check the cluster before creating manually."))
    db.session.execute(db.update(CapacityPlan).where(CapacityPlan.status == "ending").values(status="cleanup_failed"))
    # Recover only lifecycle claims made by this worker.
    for orm in db.session.scalars(db.select(MagicCastleORM).where(MagicCastleORM.creation_step == "capacity")):
        if orm.status == Status.BACKGROUND_TASK_RUNNING:
            orm.status = Status.PLAN_RUNNING if orm.tfcloud_run.run_id else Status.PLAN_ERROR
        orm.creation_step = None
    db.session.commit()


def end_plan(plan_id):
    plan = db.session.get(CapacityPlan, plan_id)
    if plan is None or plan.ends_at > time.time() or not plan.cluster_usage_id:
        return
    claimed = db.session.execute(db.update(CapacityPlan).where(
        CapacityPlan.id == plan.id, CapacityPlan.status.in_(["started", "manual_ready", "manual_starting", "failed", "cleanup_pending", "cleanup_failed"])
    ).values(status="ending"))
    db.session.commit()
    if claimed.rowcount != 1:
        return
    try:
        orm = db.session.scalar(db.select(MagicCastleORM).where(MagicCastleORM.usage_id == plan.cluster_usage_id))
        if orm is not None:
            cluster = MagicCastle(orm)
            cluster.status
            if cluster.is_busy or orm.status == Status.BACKGROUND_TASK_RUNNING:
                raise BusyClusterException
            if not orm.undeployed:
                lifecycle.claim_background_task(orm, owner="capacity")
                lifecycle.execute_claimed_task(orm.hostname, lifecycle.plan_teardown, orm.hostname, 300)
                if orm.undeployed:
                    plan.status = "ended"
                    plan.message = "The period ended; no deployed resources remain."
                    db.session.commit()
                    return
                lifecycle.validate_apply(orm)
                run_id = orm.tfcloud_run.run_id
                lifecycle.claim_background_task(orm, owner="capacity")
                lifecycle.execute_claimed_task(orm.hostname, lifecycle.apply_cluster, orm.hostname, None, run_id)
                plan.status = "cleanup_pending"
                plan.message = "Teardown requested; waiting for resources to be removed."
                db.session.commit()
                return
        plan.status = "ended"
        plan.message = "The period ended; cluster resources have been removed."
        db.session.commit()
    except BusyClusterException:
        db.session.rollback()
        plan = db.session.get(CapacityPlan, plan_id)
        plan.status = "cleanup_pending"
        plan.message = "Waiting for the current cluster operation before cleanup."
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception("Capacity plan %s cleanup deferred", plan_id)
        plan = db.session.get(CapacityPlan, plan_id)
        plan.status = "cleanup_failed"
        plan.message = "Cleanup is pending or failed; the worker will retry. Check cluster status."
        db.session.commit()


def poll_once():
    now = time.time()
    db.session.execute(db.update(CapacityPlan).where(
        CapacityPlan.status == "planned", CapacityPlan.auto_create.is_(True), CapacityPlan.ends_at <= now
    ).values(status="failed", message="The scheduled period was missed; no cluster was created."))
    db.session.commit()
    ids = list(db.session.scalars(db.select(CapacityPlan.id).where(
        CapacityPlan.status == "planned", CapacityPlan.auto_create.is_(True),
        CapacityPlan.starts_at <= now, CapacityPlan.ends_at > now)))
    cleanup_ids = list(db.session.scalars(db.select(CapacityPlan.id).where(
        CapacityPlan.cluster_usage_id.is_not(None), CapacityPlan.ends_at <= now,
        CapacityPlan.status.in_(["started", "manual_ready", "manual_starting", "failed", "cleanup_pending", "cleanup_failed"]))))
    for plan_id in cleanup_ids:
        try:
            end_plan(plan_id)
        finally:
            db.session.remove()
    for plan_id in ids:
        try:
            start_plan(plan_id)
        finally:
            db.session.remove()


def main():
    configure_worker_logging()
    app = create_app()
    with app.app_context():
        recover_interrupted()
    while True:
        with app.app_context():
            try:
                poll_once()
            except Exception:
                logger.exception("Capacity planner sweep failed")
                db.session.rollback()
        time.sleep(30)


if __name__ == "__main__":
    main()
