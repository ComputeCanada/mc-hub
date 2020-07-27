from flask import request
from resources.api_view import ApiView
from exceptions.invalid_usage_exception import InvalidUsageException
from models.magic_castle.cluster_status_code import ClusterStatusCode
from models.user.user import User


class UserAPI(ApiView):
    def get(self, user: User):
        return {"full_name": user.full_name, "username": user.username}
