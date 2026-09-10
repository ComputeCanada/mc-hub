import importlib

import pytest
from flask import Flask
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text

from mchub.database import db
from mchub.models.auth_type import AuthType
from mchub.models.cloud.project import Project, Provider
from mchub.models.user import User, UserORM
from mchub.resources.user_api import UserAPI


@pytest.fixture
def context(mocker):
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite://"
    db.init_app(app)
    mocker.patch("mchub.models.user.get_config", return_value={})
    with app.app_context():
        db.create_all()
        orm = UserORM(scoped_id="member@example.org")
        other = UserORM(scoped_id="other@example.org")
        projects = [Project(name=name, provider=Provider.OPENSTACK,
                            github_template="", tfcloud_project_id=name)
                    for name in ("first", "second", "inaccessible")]
        orm.projects.extend(projects[:2])
        other.projects.append(projects[0])
        db.session.add_all([orm, other, *projects])
        db.session.commit()
        user = User(orm, "member", "example.org", "saml")
        # Exercise the real view decorators and HTTP serialization.
        mocker.patch("mchub.resources.api_view.get_config", return_value={"auth_type": [AuthType.SAML]})
        app.add_url_rule("/api/users/me", view_func=UserAPI.as_view("user"), methods=["GET", "PATCH"])
        yield app, user, other, projects
        db.session.remove()
        db.drop_all()


HEADERS = {"eduPersonPrincipalName": "member@example.org", "givenName": "Member",
           "surname": "Test", "mail": "member@example.org"}


def test_default_is_initialized_and_preference_survives_new_requests(context):
    app, user, other, projects = context
    client = app.test_client()
    assert client.get("/api/users/me", headers=HEADERS).json["default_project_id"] == projects[0].id
    assert user.orm.default_project_id == projects[0].id
    response = client.patch("/api/users/me", headers=HEADERS, json={"default_project_id": projects[1].id})
    assert response.status_code == 200
    db.session.expire_all()
    assert client.get("/api/users/me", headers=HEADERS).json["default_project_id"] == projects[1].id
    assert User(other, "other", "example.org", "saml").default_project_id == projects[0].id


@pytest.mark.parametrize("payload", [{}, {"default_project_id": None}, {"default_project_id": True},
                                     {"default_project_id": "2"}, {"default_project_id": 3}, []])
def test_invalid_or_inaccessible_default_cannot_replace_saved_choice(context, payload):
    app, user, _, projects = context
    assert user.default_project_id == projects[0].id
    response = app.test_client().patch("/api/users/me", headers=HEADERS, json=payload)
    assert response.status_code == 400
    assert user.orm.default_project_id == projects[0].id


def test_lost_membership_and_deleted_default_are_replaced(context):
    _, user, _, projects = context
    assert user.default_project_id == projects[0].id
    user.orm.projects.remove(projects[0])
    db.session.commit()
    assert user.default_project_id == projects[1].id
    projects[2].admins.append(user.orm)
    db.session.delete(projects[1])
    db.session.commit()
    db.session.expire_all()
    assert user.default_project_id == projects[2].id


def test_first_project_becomes_default_after_user_had_no_projects(context):
    _, user, _, projects = context
    user.orm.projects.clear()
    db.session.commit()
    assert user.default_project_id is None
    projects[1].admins.append(user.orm)
    db.session.commit()
    assert user.default_project_id == projects[1].id


def test_migration_backfills_members_and_admins_and_preserves_users():
    migration = importlib.import_module("migrations.versions.0008_user_default_project")
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        for statement in (
            'CREATE TABLE "user" (id INTEGER PRIMARY KEY, scoped_id TEXT)',
            'CREATE TABLE project (id INTEGER PRIMARY KEY)',
            'CREATE TABLE projects (user_id TEXT, project_id TEXT)',
            'CREATE TABLE project_admins (user_id INTEGER, project_id INTEGER)',
            'INSERT INTO "user" VALUES (1, \'member\'), (2, \'admin\'), (3, \'empty\')',
            'INSERT INTO project VALUES (1), (2), (10)',
            'INSERT INTO projects VALUES (1, 2), (1, 10)',
            'INSERT INTO project_admins VALUES (1, 1), (2, 1)',
        ):
            connection.execute(text(statement))
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
            assert connection.execute(text('SELECT default_project_id FROM "user" ORDER BY id')).scalars().all() == [2, 1, None]
            migration.downgrade()
        assert [c["name"] for c in inspect(connection).get_columns("user")] == ["id", "scoped_id"]
        assert connection.execute(text('SELECT COUNT(*) FROM "user"')).scalar() == 3
