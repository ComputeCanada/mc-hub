import json
import pytest

from datetime import datetime
from getpass import getuser
from pathlib import Path
from os import path
from shutil import rmtree, copytree

from unittest.mock import Mock

from .mocks.github_api_mock import GithubStorageMock
from .mocks.openstack.openstack_connection_mock import OpenStackConnectionMock
from .mocks.terraform_cloud import TerraformCloudMock
from .data import CLUSTERS, BOB_HEADERS, ALICE_HEADERS, CLUSTERS_CONFIG
from mchub.models.terraform_cloud import TerraformCloudRunORM

MOCK_CLUSTERS_PATH = path.join("/tmp", "clusters")


def setup_mock_clusters(cluster_names):
    rmtree(MOCK_CLUSTERS_PATH, ignore_errors=True)
    for cluster_name in cluster_names:
        copytree(
            path.join(Path(__file__).parent, "data", "mock-clusters", cluster_name),
            path.join(MOCK_CLUSTERS_PATH, cluster_name),
        )


def teardown_mock_clusters(cluster_names):
    rmtree(MOCK_CLUSTERS_PATH, ignore_errors=True)


@pytest.fixture
def app(config_mock, generate_test_clusters):
    from mchub import create_app
    from mchub.database import db
    from mchub.models.cloud.project import Project
    from mchub.models.magic_castle.magic_castle_configuration import (
        MagicCastleConfiguration,
    )
    from mchub.models.terraform.terraform_state import TerraformState
    from mchub.models.magic_castle.magic_castle import MagicCastleORM
    from mchub.models.user import UserORM

    app = create_app(db_path="sqlite:///:memory:")
    with app.app_context():
        db.create_all()

        username = getuser()
        local_user = UserORM(scoped_id=f"{username}@localhost")
        alice_user = UserORM(scoped_id=ALICE_HEADERS["eduPersonPrincipalName"])
        bob_user = UserORM(scoped_id=BOB_HEADERS["eduPersonPrincipalName"])

        db.session.add(local_user)
        db.session.add(alice_user)
        db.session.add(bob_user)
        db.session.commit()

        project_alice = Project(
            name="project-alice",
            provider="openstack",
            env={
                "OS_AUTH_URL": "http://localhost:5000/v3",
                "OS_APPLICATION_CREDENTIAL_ID": "'z3vjwfkwqocqo2kpowkxf50uvjfkqeqt'",
                "OS_APPLICATION_CREDENTIAL_SECRET": "'ibrp7kj6labtp-s1fuu82afxrkz8w3kzjrx052ap8coljqjwiacmrxhvtf8dxce77ck8m8u6pbrgv8ezraoe4r'",
            },
            github_template="github_template",
            tfcloud_project_id="tfcloud_id",
        )
        project_bob = Project(
            name="project-bob",
            provider="openstack",
            env={
                "OS_AUTH_URL": "http://localhost:5000/v3",
                "OS_APPLICATION_CREDENTIAL_ID": "'z3vjwfkwqocqo2kpowkxf50uvjfkqeqt'",
                "OS_APPLICATION_CREDENTIAL_SECRET": "'ibrp7kj6labtp-s1fuu82afxrkz8w3kzjrx052ap8coljqjwiacmrxhvtf8dxce77ck8m8u6pbrgv8ezraoe4r'",
            },
            github_template="github_template",
            tfcloud_project_id="tfcloud_id",
        )
        project_alice.admins.append(alice_user)
        project_bob.admins.append(bob_user)
        local_user.projects.append(project_alice)
        local_user.projects.append(project_bob)
        db.session.add(project_alice)
        db.session.add(project_bob)
        db.session.commit()

        for key, data in CLUSTERS.items():
            hostname = key
            project = db.session.get(Project, data["cloud"]["id"])
            state = path.join(
                MOCK_CLUSTERS_PATH,
                hostname,
                "terraform.tfstate",
            )
            plan = path.join(
                MOCK_CLUSTERS_PATH,
                hostname,
                "terraform_plan.json",
            )
            try:
                with open(state) as file_:
                    tf_state = TerraformState(json.load(file_))
            except FileNotFoundError:
                tf_state = None
            try:
                config = MagicCastleConfiguration("", data)
            except FileNotFoundError:
                config = None
            try:
                with open(plan) as file_:
                    plan = json.load(file_)
            except FileNotFoundError:
                plan = None
            cluster = MagicCastleORM(
                hostname=hostname,
                project=project,
                status=data["status"],
                expiration_date=data["expiration_date"],
                config=config,
                created=datetime(2022, 1, 1),
                tfcloud_run=TerraformCloudRunORM(tf_state=tf_state, plan=plan),
            )
            db.session.add(cluster)
        db.session.commit()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    with app.test_client() as client:
        yield client


@pytest.fixture
def alice(app):
    from mchub.models.user import SAMLUser, UserORM
    from mchub.database import db

    yield SAMLUser(
        orm=db.session.scalar(
            db.select(UserORM).filter_by(
                scoped_id=ALICE_HEADERS["eduPersonPrincipalName"]
            )
        ),
        edu_person_principal_name=ALICE_HEADERS["eduPersonPrincipalName"],
        given_name=ALICE_HEADERS["givenName"],
        surname=ALICE_HEADERS["surname"],
        mail=ALICE_HEADERS["mail"],
        ssh_public_key=ALICE_HEADERS["sshPublicKey"],
    )


@pytest.fixture
def bob(app):
    from mchub.models.user import SAMLUser, UserORM
    from mchub.database import db

    yield SAMLUser(
        orm=db.session.scalar(
            db.select(UserORM).filter_by(
                scoped_id=BOB_HEADERS["eduPersonPrincipalName"]
            )
        ),
        edu_person_principal_name=BOB_HEADERS["eduPersonPrincipalName"],
        given_name=BOB_HEADERS["givenName"],
        surname=BOB_HEADERS["surname"],
        mail=BOB_HEADERS["mail"],
        ssh_public_key=BOB_HEADERS["sshPublicKey"],
    )


@pytest.fixture
def admin(app):
    from mchub.models.user import LocalUser, UserORM
    from mchub.database import db

    username = getuser()

    yield LocalUser(
        orm=db.session.scalar(
            db.select(UserORM).filter_by(scoped_id=f"{username}@localhost")
        ),
    )


@pytest.fixture(autouse=True)
def mock_clusters_path(mocker):
    mocker.patch("mchub.configuration.env.CLUSTERS_PATH", new=MOCK_CLUSTERS_PATH)
    mocker.patch(
        "mchub.models.magic_castle.magic_castle.CLUSTERS_PATH",
        new=MOCK_CLUSTERS_PATH,
    )


@pytest.fixture(autouse=True)
def generate_test_clusters():
    mock_cluster_names = list(CLUSTERS.keys())
    setup_mock_clusters(mock_cluster_names)
    yield
    teardown_mock_clusters(mock_cluster_names)


@pytest.fixture(autouse=True)
def mock_openstack_manager(mocker):
    mocker.patch("openstack.connect", return_value=OpenStackConnectionMock())


@pytest.fixture(autouse=True)
def mock_terraform_cloud_api(mocker):
    mocker.patch(
        "mchub.services.terraform_cloud_api._terraform_cloud_instance",
        TerraformCloudMock(),
    )


@pytest.fixture(autouse=True)
def mock_github_storage_api(mocker):
    mocker.patch(
        "mchub.services.github_api._github_storage_instance",
        GithubStorageMock(),
    )


def status_orm_return(self, *args, **kwargs):
    return self.orm.status


@pytest.fixture()
def mock_status_logic(mocker):
    from mchub.models.magic_castle.magic_castle import MagicCastle

    mocker.patch.object(
        MagicCastle, "status", new=property(lambda self: self.orm.status)
    )
    # mocker.patch.object(MagicCastle, "status", side_effect=status_orm_return)
