from re import M
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
        results = MagicCastleORM.query.all()

        for orm in results:
            mc = MagicCastle(orm)
            if mc.status == ClusterStatusCode.BUILD_RUNNING:
                mc.status = ClusterStatusCode.BUILD_ERROR
            elif mc.status == ClusterStatusCode.PLAN_RUNNING:
                mc.status = ClusterStatusCode.CREATED
            elif mc.status == ClusterStatusCode.DESTROY_RUNNING:
                mc.status = ClusterStatusCode.DESTROY_ERROR
        db.session.commit()
