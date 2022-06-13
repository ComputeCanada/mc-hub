from .api_view import ApiView
from ..exceptions.invalid_usage_exception import InvalidUsageException
from ..models.magic_castle.cluster_status_code import ClusterStatusCode
from ..models.user import User
from ..models.magic_castle.magic_castle import MagicCastleORM, MagicCastle


class ProgressAPI(ApiView):
    def get(self, user: User, hostname):
        orm = MagicCastleORM.query.filter_by(hostname=hostname).first()
        if orm and orm.project in user.projects:
            magic_castle = MagicCastle(orm)
        else:
            return {"status": ClusterStatusCode.NOT_FOUND}
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
