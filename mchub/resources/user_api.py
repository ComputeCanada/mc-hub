from .api_view import ApiView
from ..models.user import User
from ..configuration import get_config


class UserAPI(ApiView):
    def get(self, user: User):
        return {
            "username": user.username,
            "usertype": user.usertype,
            "public_keys": user.public_keys,
            "is_admin": getattr(user, "is_admin", True),
            "github_default_template": get_config().get("github_default_template"),
        }
