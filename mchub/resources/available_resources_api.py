from ..resources.api_view import APIView
from ..models.cloud.cloud_manager import CloudManager
from ..models.user import User
from ..models.cloud.project import Project
from ..models.magic_castle.magic_castle import MagicCastleORM, MagicCastle
from ..exceptions.invalid_usage_exception import (
    ClusterNotFoundException,
)
from ..database import db


class AvailableResourcesAPI(APIView):
    def get(self, user: User, hostname, cloud_id):
        if hostname:
            orm = db.session.execute(
                db.select(MagicCastleORM).filter_by(hostname=hostname)
            ).scalar_one_or_none()
            if orm and orm.project in user.projects:
                mc = MagicCastle(orm)
            else:
                raise ClusterNotFoundException
            project = mc.project
            allocated_resources = mc.allocated_resources
        else:
            project = db.session.get(Project, cloud_id)
            if project not in user.projects:
                project = None
            allocated_resources = {}
        return CloudManager(project, allocated_resources).available_resources
