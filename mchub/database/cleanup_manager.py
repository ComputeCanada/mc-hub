from .. models.magic_castle.magic_castle import MagicCastle
from .. models.magic_castle.cluster_status_code import ClusterStatusCode
from . database_manager import DatabaseManager

class CleanupManager:
    @classmethod
    def clean_status(self):
        """Look for cluster status that are running and default
        back to a stable state. Applicable when booting the app
        when and there is definetely no state running.
        """
        with DatabaseManager.connect() as db_connection:
            results = db_connection.execute("SELECT hostname FROM magic_castles").fetchall()
        for result in results:
            mc = MagicCastle(result[0])
            if mc.status == ClusterStatusCode.BUILD_RUNNING:
                mc.status = ClusterStatusCode.BUILD_ERROR
            elif mc.status == ClusterStatusCode.PLAN_RUNNING:
                mc.status = ClusterStatusCode.CREATED
            elif mc.status == ClusterStatusCode.DESTROY_RUNNING:
                mc.status = ClusterStatusCode.DESTROY_ERROR
