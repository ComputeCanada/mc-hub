from flask import request

from .api_view import ApiView
from ..models.user import User
from ..database import db
from ..exceptions.invalid_usage_exception import InvalidUsageException


class UserAPI(ApiView):
    def get(self, user: User):
        return {
            "username": user.username,
            "usertype": user.usertype,
            "public_keys": user.public_keys,
            "is_admin": getattr(user, "is_admin", True),
            "default_project_id": user.default_project_id,
        }

    def patch(self, user: User):
        if not isinstance(user, User):
            raise InvalidUsageException("A user account is required to save preferences.", status_code=403)
        data = request.get_json()
        project_id = data.get("default_project_id") if isinstance(data, dict) else None
        if type(project_id) is not int or not any(p.id == project_id for p in user.projects):
            raise InvalidUsageException("Choose an accessible project as your default.")
        user.orm.default_project_id = project_id
        db.session.commit()
        return {"default_project_id": project_id}
