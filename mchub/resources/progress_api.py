from .api_view import ApiView
from ..exceptions.invalid_usage_exception import InvalidUsageException
from ..models.magic_castle.cluster_status_code import ClusterStatusCode
from ..models.user import User


class ProgressAPI(ApiView):
    def get(self, user: User, hostname):
        try:
            magic_castle = user.query_magic_castles(hostname=hostname)[0]
        except (IndexError, InvalidUsageException) as e:
            return {"status": ClusterStatusCode.NOT_FOUND}
        else:
            status = magic_castle.status
            progress = magic_castle.get_progress()
            stateful = magic_castle.tf_state is not None
            if progress is None:
                return {"status": status, "stateful": stateful}
            else:
                return {
                    "status": status,
                    "stateful": stateful,
                    "progress": progress,
                }
