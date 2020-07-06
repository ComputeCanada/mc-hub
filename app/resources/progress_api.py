from flask import request
from resources.api_view import ApiView
from exceptions.invalid_usage_exception import InvalidUsageException
from models.magic_castle import MagicCastle
from models.cluster_status_code import ClusterStatusCode


class ProgressAPI(ApiView):
    def get(self, hostname):
        magic_castle = MagicCastle(hostname)
        status = magic_castle.get_status()
        if status == ClusterStatusCode.NOT_FOUND:
            return {
                "status": status.value,
            }
        else:
            progress = magic_castle.get_progress()
            if progress is None:
                return {"status": status.value}
            else:
                return {"status": status.value, "progress": progress}
