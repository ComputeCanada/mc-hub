from .api_view import APIView
from ..models.magic_castle.cluster_status_code import ClusterStatusCode
from ..models.user import User
from ..models.magic_castle.magic_castle import MagicCastleORM, MagicCastle
from ..database import db


class ProgressAPI(APIView):
    def get(self, user: User, hostname):
        orm = db.session.execute(
            db.select(MagicCastleORM).filter_by(hostname=hostname)
        ).scalar_one_or_none()
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
