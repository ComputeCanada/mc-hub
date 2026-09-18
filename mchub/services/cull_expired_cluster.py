"""Expire deployments through shared lifecycle services, without loopback HTTP."""
import logging
import time
from datetime import datetime

from .. import create_app
from ..database import db
from ..exceptions.invalid_usage_exception import BusyClusterException
from ..models.magic_castle.magic_castle import MagicCastle, MagicCastleORM
from ..models.magic_castle.cluster_status_code import ClusterStatusCode as Status
from . import cluster_lifecycle as lifecycle

logger = logging.getLogger(__name__)
SWEEP_INTERVAL = 3600
PLAN_WAIT_TIMEOUT = 5 * 60


def is_expired(orm, now):
    return (not orm.undeployed and orm.expiration_date is not None
            and datetime.strptime(orm.expiration_date, "%Y-%m-%d") < now)


def expire_cluster(orm, now):
    # Refresh remote progress before deciding whether the cluster is busy/empty.
    cluster = MagicCastle(orm)
    cluster.status
    if not is_expired(orm, now):
        return
    hostname = orm.hostname
    lifecycle.claim_background_task(orm, owner="expiration")
    logger.info("Tearing down expired cluster %s", hostname)
    lifecycle.execute_claimed_task(hostname, lifecycle.plan_teardown, hostname, PLAN_WAIT_TIMEOUT)

    orm = lifecycle.get_cluster(hostname)
    if orm.undeployed or orm.status == Status.NOT_DEPLOYED:
        return
    # plan_destruction returns only after the destroy plan is available.
    run_id = orm.tfcloud_run.run_id
    lifecycle.validate_apply(orm)
    # A user can extend expiration while planning finishes. Recheck before apply.
    db.session.refresh(orm)
    if not is_expired(orm, datetime.now()):
        return
    lifecycle.claim_background_task(orm, owner="expiration")
    lifecycle.execute_claimed_task(hostname, lifecycle.apply_cluster, hostname, None, run_id)


def poll_once():
    ids = list(db.session.scalars(db.select(MagicCastleORM.id).where(
        MagicCastleORM.expiration_date.is_not(None), MagicCastleORM.undeployed.is_(False),
    )))
    for cluster_id in ids:
        try:
            orm = db.session.get(MagicCastleORM, cluster_id)
            if orm is not None and is_expired(orm, datetime.now()):
                expire_cluster(orm, datetime.now())
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
    for orm in db.session.scalars(db.select(MagicCastleORM).where(
        MagicCastleORM.creation_step == "expiration",
    )):
        if orm.status == Status.BACKGROUND_TASK_RUNNING:
            orm.status = Status.PLAN_RUNNING if orm.tfcloud_run.run_id else Status.PLAN_ERROR
        orm.creation_step = None
    db.session.commit()


def main(interval=SWEEP_INTERVAL):
    logging.basicConfig(level=logging.INFO)
    app = create_app()
    with app.app_context():
        recover_interrupted_expiration()
    while True:
        with app.app_context():
            try:
                poll_once()
            except Exception:
                db.session.rollback()
                logger.exception("Expiration sweep failed")
        time.sleep(interval)


if __name__ == "__main__":
    main()
