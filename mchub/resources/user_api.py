from .api_view import APIView
from ..models.user import User


class UserAPI(APIView):
    def get(self, user: User):
        return {
            "username": user.username,
            "usertype": user.usertype,
            "public_keys": user.public_keys,
        }
