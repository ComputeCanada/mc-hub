"""Lifecycle coordination shared by HTTP handlers and background workers.

Callers authorize the operation before claiming it. These functions enforce
mutual exclusion and plan validation, not user permissions.
"""
from datetime import timedelta
import secrets

from ..database import db
from ..exceptions.invalid_usage_exception import (
    BusyClusterException, ClusterNotFoundException, InvalidUsageException,
    PlanNotCreatedException, PlanNotReadyException, RunIDNotSet,
)
from ..models.magic_castle.magic_castle import MagicCastle, MagicCastleORM
from ..models.magic_castle.cluster_status_code import ClusterStatusCode as Status
from .terraform_cloud_api import get_terraform_cloud


def get_cluster(hostname):
    orm = db.session.scalar(db.select(MagicCastleORM).filter_by(hostname=hostname))
    if orm is None:
        raise ClusterNotFoundException
    return orm


def claim_background_task(orm, owner=None):
    from . import plan_recovery
    if (orm.benchmark_id or orm.benchmark_run_id) and owner != "benchmark":
        raise InvalidUsageException("This cluster is managed by its benchmark.", status_code=403)
    if orm.status == Status.BACKGROUND_TASK_RUNNING or MagicCastle(orm).is_busy:
        raise BusyClusterException
    result = db.session.execute(
        db.update(MagicCastleORM)
        .where(MagicCastleORM.id == orm.id, MagicCastleORM.usage_id == orm.usage_id,
               MagicCastleORM.status == orm.status,
               MagicCastleORM.expiration_date == orm.expiration_date)
        .values(status=Status.BACKGROUND_TASK_RUNNING, creation_step=owner)
        .execution_options(synchronize_session=False)
    )
    if result.rowcount != 1:
        db.session.rollback()
        raise BusyClusterException
    # Fence new claims before any external work. Legacy rows without a lease
    # are recoverable immediately after upgrading stopped workers.
    if orm.tfcloud_run is not None:
        orm.tfcloud_run.lease_owner = secrets.token_hex(16)
        orm.tfcloud_run.lease_until = plan_recovery.now() + timedelta(seconds=360)
    db.session.commit()


def validate_apply(orm):
    cluster = MagicCastle(orm)
    if orm.status == Status.BACKGROUND_TASK_RUNNING or cluster.is_busy:
        raise BusyClusterException
    if orm.status != Status.CREATED:
        raise PlanNotReadyException
    if cluster.plan is None:
        raise PlanNotCreatedException
    if cluster.tfcloud_run.run_id is None:
        raise RunIDNotSet
    from .capacity import validate_plan_apply
    validate_plan_apply(orm)


def execute_claimed_task(hostname, target, *args):
    """Execute an already-claimed operation and persist its terminal status."""
    from . import plan_recovery
    claimed = get_cluster(hostname).tfcloud_run if hostname is not None else None
    claim = (claimed.id, claimed.lease_owner) if claimed is not None else None
    ownership_lost = False
    try:
        return target(*args)
    except plan_recovery.PlanOwnershipLost:
        ownership_lost = True
        db.session.rollback()
        return
    except Exception:
        db.session.rollback()
        if hostname is not None:
            orm = db.session.scalar(db.select(MagicCastleORM).filter_by(hostname=hostname))
            if orm is not None:
                orm.status = Status.PLAN_ERROR
                db.session.commit()
        raise
    finally:
        owns_claim = False
        if claim is not None:
            from ..models.terraform_cloud import TerraformCloudRunORM
            owns_claim = db.session.scalar(db.select(TerraformCloudRunORM.id).where(
                TerraformCloudRunORM.id == claim[0], TerraformCloudRunORM.lease_owner == claim[1],
            )) is not None
            plan_recovery.release(*claim)
        if not ownership_lost and hostname is not None:
            orm = db.session.scalar(db.select(MagicCastleORM).filter_by(hostname=hostname))
            if orm is not None:
                if owns_claim and orm.status == Status.BACKGROUND_TASK_RUNNING:
                    orm.status = Status.PLAN_RUNNING
                if orm.creation_step in {"expiration", "capacity"}:
                    orm.creation_step = None
                db.session.commit()


def plan_teardown(hostname, timeout=None):
    MagicCastle(get_cluster(hostname)).plan_destruction(timeout=timeout)


def apply_cluster(hostname, initiated_by=None, expected_destroy_run=None):
    orm = get_cluster(hostname)
    if expected_destroy_run is not None:
        if orm.tfcloud_run.run_id != expected_destroy_run:
            raise InvalidUsageException("The expiration teardown run changed; refusing to apply it")
        _, is_destroy = get_terraform_cloud().get_run_status(expected_destroy_run)
        if not is_destroy:
            raise InvalidUsageException("Expiration can only apply a destroy run")
    MagicCastle(orm).apply(initiated_by=initiated_by)
