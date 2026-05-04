from flask import request

from .api_view import ApiView
from ..database import db
from ..models.user import User, UserORM
from ..services.terraform_cloud_api import get_terraform_cloud, TerraformCloudVariable
from ..services.github_api import get_github_storage
from ..models.cloud.project import Project, Provider, ENV_VALIDATORS
from ..exceptions.invalid_usage_exception import (
    InvalidUsageException,
)
from ..exceptions.server_exception import (
    TerraformCloudException,
    GithubStorageException,
)


class ProjectAPI(ApiView):
    def get(self, user: User, id: int = None):
        if id is not None:
            project = db.session.get(Project, id)
            if project is None or project not in user.projects:
                raise InvalidUsageException("Invalid project id")
            is_admin = user.is_project_admin(project)
            return {
                "id": project.id,
                "name": project.name,
                "provider": project.provider,
                "github_template": project.github_template,
                "nb_clusters": len(project.magic_castles),
                "admin": is_admin,
                "members": [member.scoped_id for member in project.members]
                if is_admin
                else [],
                "admins": [admin.scoped_id for admin in project.admins]
                if is_admin
                else [],
            }
        else:
            return [
                {
                    "id": project.id,
                    "name": project.name,
                    "provider": project.provider,
                    "github_template": project.github_template,
                    "nb_clusters": len(project.magic_castles),
                    "admin": user.is_project_admin(project),
                }
                for project in user.projects
            ]

    def post(self, user: User):
        if not getattr(user, "is_admin", False):
            raise InvalidUsageException(
                "Only admins can create projects", status_code=403
            )
        data = request.get_json()
        if not data:
            raise InvalidUsageException("No json data was provided")
        try:
            provider = Provider(data["provider"])
            env = data["env"]
            name = data["name"]
            github_template = data["github_template"]
        except KeyError as err:
            raise InvalidUsageException(f"Missing required field {err}")
        agent_pool_name = data.get("agent_pool_name")

        try:
            env = ENV_VALIDATORS[provider](env)
        except Exception as err:
            raise InvalidUsageException("Missing required environment variables")

        if github_template:
            try:
                get_github_storage().validate_template(github_template)
            except GithubStorageException as e:
                raise InvalidUsageException(str(e))

        try:
            tfcloud_project_id = get_terraform_cloud().create_project(
                name, agent_pool_name=agent_pool_name
            )
        except TerraformCloudException:
            raise InvalidUsageException(f"Error with Terraform Cloud project creation")

        terraform_vars = []
        for k, v in env.items():
            sensitive = True if "SECRET" in k else False
            terraform_vars.append(
                TerraformCloudVariable(name=k, value=v, sensitive=sensitive)
            )
        get_terraform_cloud().set_project_variable_set(
            tfcloud_project_id, name, terraform_vars
        )

        if user.orm.id is None:
            db.session.add(user.orm)
            db.session.commit()

        project = Project(
            name=name,
            provider=provider,
            env=env,
            github_template=github_template,
            tfcloud_project_id=tfcloud_project_id,
        )
        project.admins.append(user.orm)
        db.session.add(project)
        db.session.commit()
        return {
            "id": project.id,
            "name": project.name,
            "provider": project.provider,
            "github_template": project.github_template,
            "nb_clusters": len(project.magic_castles),
            "admin": True,
        }, 200

    def patch(self, user: User, id: int):
        project = db.session.get(Project, id)
        if project is None or project not in user.projects:
            raise InvalidUsageException("Invalid project id")
        if not user.is_project_admin(project):
            raise InvalidUsageException(
                "Cannot edit project membership that you are not the admin of"
            )
        data = request.get_json()
        if not data:
            raise InvalidUsageException("No json data was provided")

        if "github_template" in data:
            if data["github_template"]:
                try:
                    get_github_storage().validate_template(data["github_template"])
                except GithubStorageException as e:
                    raise InvalidUsageException(str(e))
            project.github_template = data["github_template"]

        if "agent_pool_name" in data:
            try:
                get_terraform_cloud().update_project(project.tfcloud_project_id, data["agent_pool_name"])
            except TerraformCloudException:
                raise InvalidUsageException("Error updating agent pool")

        if "env" in data:
            try:
                env = ENV_VALIDATORS[project.provider](data["env"])
            except Exception:
                raise InvalidUsageException("Missing required environment variables")
            terraform_vars = [
                TerraformCloudVariable(name=k, value=v, sensitive="SECRET" in k)
                for k, v in env.items()
            ]
            get_terraform_cloud().replace_project_variable_set(
                project.tfcloud_project_id, project.name, terraform_vars
            )
            project.env = env

        add_members = data.get("add", [])
        del_members = data.get("del", [])
        add_admins = data.get("add_admins", [])
        del_admins = data.get("del_admins", [])

        default_domain = user.domain

        for username in add_members:
            if "@" not in username:
                username = f"{username}@{default_domain}"
            member = db.session.execute(
                db.select(UserORM).filter_by(scoped_id=username)
            ).scalar_one_or_none()
            if not member:
                member = UserORM(scoped_id=username)
                db.session.add(member)
            if project not in member.projects:
                member.projects.append(project)

        for username in del_members:
            if "@" not in username:
                username = f"{username}@{default_domain}"
            member = db.session.execute(
                db.select(UserORM).filter_by(scoped_id=username)
            ).scalar_one_or_none()
            if member and member.id != user.orm.id:
                if project in member.projects:
                    member.projects.remove(project)
                if member in project.admins:
                    project.admins.remove(member)

        for username in add_admins:
            if "@" not in username:
                username = f"{username}@{default_domain}"
            member = db.session.execute(
                db.select(UserORM).filter_by(scoped_id=username)
            ).scalar_one_or_none()
            if not member:
                member = UserORM(scoped_id=username)
                db.session.add(member)
            if project in member.projects:
                member.projects.remove(project)
            if member not in project.admins:
                project.admins.append(member)

        for username in del_admins:
            if "@" not in username:
                username = f"{username}@{default_domain}"
            member = db.session.execute(
                db.select(UserORM).filter_by(scoped_id=username)
            ).scalar_one_or_none()
            if member and member.id != user.orm.id and member in project.admins:
                project.admins.remove(member)
                if project not in member.projects:
                    member.projects.append(project)

        db.session.commit()
        return {}, 200

    def delete(self, user: User, id: int):
        project = db.session.get(Project, id)
        if project is None or project not in user.projects:
            raise InvalidUsageException("Invalid project id")
        if not user.is_project_admin(project):
            raise InvalidUsageException(
                "Cannot remove project that you are not the admin of"
            )
        if len(project.magic_castles) > 0:
            raise InvalidUsageException("Cannot remove project with running clusters")
        user.orm.projects.remove(project)
        db.session.delete(project)
        db.session.commit()
        return {}, 200