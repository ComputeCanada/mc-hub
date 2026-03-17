from .api_view import ApiView
from ..models.user import User


class UserAPI(ApiView):
    def get(self, user: User):
        return {
            "username": user.username,
            "usertype": user.usertype,
            "public_keys": user.public_keys,
            "is_admin": getattr(user, "is_admin", True),
        }
