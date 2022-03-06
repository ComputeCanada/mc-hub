import sqlite3
from .. models.magic_castle.magic_castle import MagicCastle
from .. models.magic_castle.cluster_status_code import ClusterStatusCode

class CleanupManager:
    def __init__(self, database_connection: sqlite3.Connection):
        self.db_connection = database_connection

    def clean_state(self):
        """Look for cluster states that are running and default
        back to a stable state. Applicable when booting the app
        when and there is definetely no state running.
        """
        for result in self.db_connection.execute("SELECT hostname FROM magic_castles"):
            mc = MagicCastle(result[0])
            status = mc.status
            if status == ClusterStatusCode.BUILD_RUNNING:
                mc.status = ClusterStatusCode.BUILD_ERROR
            elif status == ClusterStatusCode.PLAN_RUNNING:
                mc.status = ClusterStatusCode.CREATED
            elif status == ClusterStatusCode.DESTROY_RUNNING:
                mc.status = ClusterStatusCode.DESTROY_ERROR
