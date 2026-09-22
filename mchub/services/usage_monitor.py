"""Poll cluster readiness without depending on page visits."""
import logging
import time

from .. import create_app
from ..database import db
from ..models.magic_castle.magic_castle import MagicCastle, MagicCastleORM
from ..models.magic_castle.cluster_status_code import ClusterStatusCode as Status
from . import usage
from .worker_logging import configure_worker_logging

logger = logging.getLogger(__name__)


def poll_once():
    ids = list(db.session.scalars(db.select(MagicCastleORM.id)))
    for cluster_id in ids:
        try:
            orm = db.session.get(MagicCastleORM, cluster_id)
            if orm is None:
                continue
            status = MagicCastle(orm).status
            if orm.usage_legacy and not orm.undeployed and (
                Status.is_provisioning(status) or orm.applied_config is not None
            ):
                usage.ensure_lifetime(orm)
                db.session.commit()
        except Exception:
            db.session.rollback()
            logger.exception("Usage observer could not refresh cluster %s", cluster_id)
        finally:
            db.session.remove()
    usage.state().last_poll_at = usage.utcnow()
    db.session.commit()


def main():
    configure_worker_logging()
    app = create_app()
    while True:
        with app.app_context():
            try:
                poll_once()
            except Exception:
                db.session.rollback()
                logger.exception("Usage observer sweep failed")
        time.sleep(usage.POLL_INTERVAL)


if __name__ == "__main__":
    main()
