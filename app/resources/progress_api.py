from flask import request
from resources.api_view import ApiView
from exceptions.invalid_usage_exception import InvalidUsageException
from models.magic_castle.cluster_status_code import ClusterStatusCode
from models.user.user import User


class ProgressAPI(ApiView):
    def get(self, user: User, hostname):
        try:
            magic_castle = user.get_magic_castle_by_hostname(hostname)
            status = magic_castle.get_status()
            progress = magic_castle.get_progress()
            if progress is None:
                return {"status": status.value}
            else:
                return {"status": status.value, "progress": progress}
        except InvalidUsageException as e:
            return {"status": ClusterStatusCode.NOT_FOUND.value}
