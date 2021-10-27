from resources.api_view import ApiView
from models.user.user import User


class UserAPI(ApiView):
    def get(self, user: User):
        return {
            "full_name": user.full_name,
            "username": user.username,
            "public_keys": user.public_keys
        }
