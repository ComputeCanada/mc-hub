import json
import pytest
import sqlite3

from getpass import getuser
from pathlib import Path
from os import path
from shutil import rmtree, copytree
from typing import Callable

from mchub import create_app
from mchub.database import db
from mchub.models.user import SAMLUser, UserORM
from mchub.models.magic_castle.magic_castle_configuration import (
    MagicCastleConfiguration,
)
from mchub.models.cloud.project import Project
from mchub.models.magic_castle.magic_castle import MagicCastleORM
from mchub.models.terraform.terraform_state import TerraformState
from mchub.models.magic_castle.cluster_status_code import ClusterStatusCode
from mchub.models.magic_castle.plan_type import PlanType

from unittest.mock import Mock
from .mocks.openstack.openstack_connection_mock import OpenStackConnectionMock
from .data import CLUSTERS, PLAN_TYPE, BOB_HEADERS, ALICE_HEADERS

MOCK_CLUSTERS_PATH = path.join("/tmp", "clusters")


def setup_mock_clusters(cluster_names):
    rmtree(MOCK_CLUSTERS_PATH, ignore_errors=True)
    for cluster_name in cluster_names:
        copytree(
            path.join(Path(__file__).parent, "data", "mock-clusters", cluster_name),
            path.join(MOCK_CLUSTERS_PATH, cluster_name),
        )


def teardown_mock_clusters(cluster_names):
    for cluster_name in cluster_names:
        rmtree(path.join(MOCK_CLUSTERS_PATH, cluster_name))


def create_test_app():

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
            admin_id=alice_user.id,
            provider="openstack",
            env={
                "OS_AUTH_URL": "http://localhost:5000/v3",
                "OS_APPLICATION_CREDENTIAL_ID": "'z3vjwfkwqocqo2kpowkxf50uvjfkqeqt'",
                "OS_APPLICATION_CREDENTIAL_SECRET": "'ibrp7kj6labtp-s1fuu82afxrkz8w3kzjrx052ap8coljqjwiacmrxhvtf8dxce77ck8m8u6pbrgv8ezraoe4r'",
            },
        )
        project_bob = Project(
            name="project-bob",
            provider="openstack",
            admin_id=bob_user.id,
            env={
                "OS_AUTH_URL": "http://localhost:5000/v3",
                "OS_APPLICATION_CREDENTIAL_ID": "'z3vjwfkwqocqo2kpowkxf50uvjfkqeqt'",
                "OS_APPLICATION_CREDENTIAL_SECRET": "'ibrp7kj6labtp-s1fuu82afxrkz8w3kzjrx052ap8coljqjwiacmrxhvtf8dxce77ck8m8u6pbrgv8ezraoe4r'",
            },
        )
        local_user.projects.append(project_alice)
        local_user.projects.append(project_bob)
        alice_user.projects.append(project_alice)
        bob_user.projects.append(project_bob)
        db.session.add(project_alice)
        db.session.add(project_bob)
        db.session.commit()

        for key, data in CLUSTERS.items():
            hostname = key
            project = Project.query.get(data["cloud"]["id"])
            main = path.join(
                MOCK_CLUSTERS_PATH,
                hostname,
                "main.tf.json",
            )
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
                config = MagicCastleConfiguration.get_from_main_file(main)
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
                tf_state=tf_state,
                plan_type=PLAN_TYPE[key],
                plan=plan,
            )
            db.session.add(cluster)
        db.session.commit()
    return app


@pytest.fixture
def client(mocker):
    app = create_test_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def alice() -> Callable[[sqlite3.Connection], SAMLUser]:
    app = create_test_app()
    with app.app_context():
        yield SAMLUser(
            orm=UserORM.query.get(2),
            edu_person_principal_name=ALICE_HEADERS["eduPersonPrincipalName"],
            given_name=ALICE_HEADERS["givenName"],
            surname=ALICE_HEADERS["surname"],
            mail=ALICE_HEADERS["mail"],
            ssh_public_key=ALICE_HEADERS["sshPublicKey"],
        )


@pytest.fixture
def bob() -> Callable[[sqlite3.Connection], SAMLUser]:
    app = create_test_app()
    with app.app_context():
        yield SAMLUser(
            orm=UserORM.query.get(3),
            edu_person_principal_name=BOB_HEADERS["eduPersonPrincipalName"],
            given_name=BOB_HEADERS["givenName"],
            surname=BOB_HEADERS["surname"],
            mail=BOB_HEADERS["mail"],
            ssh_public_key=BOB_HEADERS["sshPublicKey"],
        )


@pytest.fixture
def admin() -> Callable[[sqlite3.Connection], SAMLUser]:
    app = create_test_app()
    with app.app_context():
        yield SAMLUser(
            orm=UserORM.query.get(1),
            edu_person_principal_name="the-admin@computecanada.ca",
            given_name="Admin",
            surname="Istrator",
            mail="administrator@example.com",
            ssh_public_key="ssh-rsa FAKE",
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
    mock_cluster_names = [
        "buildplanning.calculquebec.cloud",
        "created.calculquebec.cloud",
        "empty-state.calculquebec.cloud",
        "missingnodes.c3.ca",
        "noowner.calculquebec.cloud",
        "valid1.calculquebec.cloud",
        "missingfloatingips.c3.ca",
    ]
    setup_mock_clusters(mock_cluster_names)
    yield
    teardown_mock_clusters(mock_cluster_names)


@pytest.fixture(autouse=True)
def mock_openstack_manager(mocker):
    mocker.patch("openstack.connect", return_value=OpenStackConnectionMock())


@pytest.fixture
def fake_successful_subprocess_run(mocker):
    mock = Mock()
    mock.stdout = "{}"
    mocker.patch("mchub.models.magic_castle.magic_castle.run", return_value=mock)
