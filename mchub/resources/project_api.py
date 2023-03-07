from flask import request
from sqlalchemy import inspect

from .api_view import ApiView
from ..database import db
from ..models.user import User, UserORM
from ..models.cloud.project import Project, Provider, ENV_VALIDATORS
from ..exceptions.invalid_usage_exception import (
    InvalidUsageException,
)


class ProjectAPI(ApiView):
    def get(self, user: User, id: int = None):
        if id is not None:
            project = db.session.get(Project, id)
            if project is None or project not in user.orm.projects:
                raise InvalidUsageException("Invalid project id")
            return {
                "id": project.id,
                "name": project.name,
                "provider": project.provider,
                "nb_clusters": len(project.magic_castles),
                "admin": project.admin_id == user.orm.id,
                "members": [member.scoped_id for member in project.members]
                if project.admin_id == user.orm.id
                else [],
            }
        else:
            return [
                {
                    "id": project.id,
                    "name": project.name,
                    "provider": project.provider,
                    "nb_clusters": len(project.magic_castles),
                    "admin": project.admin_id == user.orm.id,
                }
                for project in user.projects
            ]

    def post(self, user: User):
        data = request.get_json()
        if not data:
            raise InvalidUsageException("No json data was provided")
        try:
            provider = Provider(data["provider"])
            env = data["env"]
            name = data["name"]
        except KeyError as err:
            raise InvalidUsageException(f"Missing required field {err}")

        try:
            env = ENV_VALIDATORS[provider](env)
        except Exception as err:
            raise InvalidUsageException("Missing required environment variables")

        if user.orm.id is None:
            db.session.add(user.orm)
            db.session.commit()

        project = Project(name=name, admin_id=user.orm.id, provider=provider, env=env)
        user.orm.projects.append(project)
        db.session.add(project)
        db.session.commit()
        return {
            "id": project.id,
            "name": project.name,
            "provider": project.provider,
            "nb_clusters": len(project.magic_castles),
            "admin": project.admin_id == user.orm.id,
        }, 200

    def patch(self, user: User, id: int):
        project = Project.query.get(id)
        if project is None or project not in user.orm.projects:
            raise InvalidUsageException("Invalid project id")
        if project.admin_id != user.orm.id:
            raise InvalidUsageException(
                "Cannot edit project membership that you are not the admin of"
            )
        data = request.get_json()
        if not data:
            raise InvalidUsageException("No json data was provided")

        add_members = data.get("add", [])
        del_members = data.get("del", [])

        default_domain = user.domain

        for username in add_members:
            if "@" not in username:
                username = f"{username}@{default_domain}"
            member = UserORM.query.filter_by(scoped_id=username).first()
            if not member:
                member = UserORM(scoped_id=username)
                db.session.add(member)
            member.projects.append(project)

        for username in del_members:
            if "@" not in username:
                username = f"{username}@{default_domain}"
            member = UserORM.query.filter_by(scoped_id=username).first()
            if member and member.id != user.orm.id:
                member.projects.remove(project)

        db.session.commit()
        return {}, 200

    def delete(self, user: User, id: int):
        project = Project.query.get(id)
        if project is None or project not in user.orm.projects:
            raise InvalidUsageException("Invalid project id")
        if project.admin_id != user.orm.id:
            raise InvalidUsageException(
                "Cannot remove project that you are not the admin of"
            )
        if len(project.magic_castles) > 0:
            raise InvalidUsageException("Cannot remove project with running clusters")
        user.orm.projects.remove(project)
        db.session.delete(project)
        db.session.commit()
        return {}, 200
