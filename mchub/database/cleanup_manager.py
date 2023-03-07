from re import M
from sqlalchemy import select

from ..models.magic_castle.magic_castle import MagicCastle, MagicCastleORM
from ..models.magic_castle.cluster_status_code import ClusterStatusCode
from . import db


class CleanupManager:
    @classmethod
    def clean_status(self):
        """Look for cluster status that are running and default
        back to a stable state. Applicable when booting the app
        when and there is definetely no state running.
        """
        for orm in MagicCastleORM.query.all():
            if orm.status == ClusterStatusCode.BUILD_RUNNING:
                orm.status = ClusterStatusCode.BUILD_ERROR
            elif orm.status == ClusterStatusCode.PLAN_RUNNING:
                orm.status = ClusterStatusCode.CREATED
            elif orm.status == ClusterStatusCode.DESTROY_RUNNING:
                orm.status = ClusterStatusCode.DESTROY_ERROR
        db.session.commit()
