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

MOCK_CLUSTERS_PATH = path.join("/tmp", "clusters")


def setup_mock_clusters(cluster_names):
    rmtree(MOCK_CLUSTERS_PATH, ignore_errors=True)
    for cluster_name in cluster_names:
        copytree(
            path.join(Path(__file__).parent, "mock-clusters", cluster_name),
            path.join(MOCK_CLUSTERS_PATH, cluster_name),
        )


def teardown_mock_clusters(cluster_names):
    for cluster_name in cluster_names:
        rmtree(path.join(MOCK_CLUSTERS_PATH, cluster_name))


def create_test_app():

    app = create_app(db_path="sqlite:///:memory:")
    with app.app_context():
        db.create_all()

        project_alice = Project(
            name="project-alice",
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
            env={
                "OS_AUTH_URL": "http://localhost:5000/v3",
                "OS_APPLICATION_CREDENTIAL_ID": "'z3vjwfkwqocqo2kpowkxf50uvjfkqeqt'",
                "OS_APPLICATION_CREDENTIAL_SECRET": "'ibrp7kj6labtp-s1fuu82afxrkz8w3kzjrx052ap8coljqjwiacmrxhvtf8dxce77ck8m8u6pbrgv8ezraoe4r'",
            },
        )
        db.session.add(project_alice)
        db.session.add(project_bob)
        db.session.commit()

        username = getuser()
        local_user = UserORM(
            scoped_id=f"{username}@localhost", projects=[project_alice, project_bob]
        )
        alice_user = UserORM(
            scoped_id="alice@computecanada.ca", projects=[project_alice]
        )
        bob_user = UserORM(scoped_id="bob@computecanada.ca", projects=[project_bob])

        db.session.add(local_user)
        db.session.add(alice_user)
        db.session.add(bob_user)
        db.session.commit()

        # Using an in-memory database for faster unit tests with less disk IO
        buildplanning = MagicCastleORM(
            hostname="buildplanning.calculquebec.cloud",
            plan_type=PlanType.BUILD,
            status=ClusterStatusCode.PLAN_RUNNING,
            expiration_date="2029-01-01",
            project=project_alice,
            config=MagicCastleConfiguration.get_from_main_file(
                path.join(
                    MOCK_CLUSTERS_PATH,
                    "buildplanning.calculquebec.cloud",
                    "main.tf.json",
                )
            ),
        )
        created = MagicCastleORM(
            hostname="created.calculquebec.cloud",
            status=ClusterStatusCode.CREATED,
            plan_type=PlanType.BUILD,
            expiration_date="2029-01-01",
            project=project_alice,
            config=MagicCastleConfiguration.get_from_main_file(
                path.join(
                    MOCK_CLUSTERS_PATH, "created.calculquebec.cloud", "main.tf.json"
                )
            ),
        )
        empty_state = MagicCastleORM(
            hostname="empty-state.calculquebec.cloud",
            status=ClusterStatusCode.BUILD_ERROR,
            plan_type=PlanType.NONE,
            expiration_date="2029-01-01",
            project=project_bob,
            config=MagicCastleConfiguration.get_from_main_file(
                path.join(
                    MOCK_CLUSTERS_PATH, "empty-state.calculquebec.cloud", "main.tf.json"
                )
            ),
        )
        empty = MagicCastleORM(
            hostname="empty.calculquebec.cloud",
            status=ClusterStatusCode.BUILD_ERROR,
            plan_type=PlanType.NONE,
            expiration_date="2029-01-01",
            project=project_bob,
            config={},
        )
        missingfip = MagicCastleORM(
            hostname="missingfloatingips.c3.ca",
            status=ClusterStatusCode.BUILD_RUNNING,
            plan_type=PlanType.NONE,
            expiration_date="2029-01-01",
            project=project_bob,
            config=MagicCastleConfiguration.get_from_main_file(
                path.join(
                    MOCK_CLUSTERS_PATH, "missingfloatingips.c3.ca", "main.tf.json"
                )
            ),
        )
        main_tf = path.join(MOCK_CLUSTERS_PATH, "missingnodes.c3.ca", "main.tf.json")
        terraform_tf = path.join(
            MOCK_CLUSTERS_PATH, "missingnodes.c3.ca", "terraform.tfstate"
        )
        with open(path.join(terraform_tf)) as file_:
            tf_state = TerraformState(json.load(file_))
        missingnodes = MagicCastleORM(
            hostname="missingnodes.c3.ca",
            status=ClusterStatusCode.BUILD_ERROR,
            plan_type=PlanType.NONE,
            expiration_date="2029-01-01",
            project=project_bob,
            config=MagicCastleConfiguration.get_from_main_file(main_tf),
            tf_state=tf_state,
        )

        hostname = "noowner.calculquebec.cloud"
        main_tf = path.join(MOCK_CLUSTERS_PATH, hostname, "main.tf.json")
        terraform_tf = path.join(MOCK_CLUSTERS_PATH, hostname, "terraform.tfstate")
        with open(path.join(terraform_tf)) as file_:
            tf_state = TerraformState(json.load(file_))
        noower = MagicCastleORM(
            hostname=hostname,
            status=ClusterStatusCode.PROVISIONING_SUCCESS,
            plan_type=PlanType.DESTROY,
            expiration_date="2029-01-01",
            project=project_bob,
            config=MagicCastleConfiguration.get_from_main_file(main_tf),
            tf_state=tf_state,
        )

        hostname = "valid1.calculquebec.cloud"
        main_tf = path.join(MOCK_CLUSTERS_PATH, hostname, "main.tf.json")
        terraform_tf = path.join(MOCK_CLUSTERS_PATH, hostname, "terraform.tfstate")
        with open(path.join(terraform_tf)) as file_:
            tf_state = TerraformState(json.load(file_))
        valid1 = MagicCastleORM(
            hostname=hostname,
            status=ClusterStatusCode.PROVISIONING_SUCCESS,
            plan_type=PlanType.DESTROY,
            expiration_date="2029-01-01",
            project=project_alice,
            config=MagicCastleConfiguration.get_from_main_file(main_tf),
            tf_state=tf_state,
        )

        db.session.add(buildplanning)
        db.session.add(created)
        db.session.add(empty_state)
        db.session.add(empty)
        db.session.add(missingfip)
        db.session.add(missingnodes)
        db.session.add(noower)
        db.session.add(valid1)
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
    return SAMLUser(
        orm=None,
        edu_person_principal_name="alice@computecanada.ca",
        given_name="Alice",
        surname="Tremblay",
        mail="alice.tremblay@example.com",
        ssh_public_key="ssh-rsa FAKE",
    )


@pytest.fixture
def bob() -> Callable[[sqlite3.Connection], SAMLUser]:
    return SAMLUser(
        orm=None,
        edu_person_principal_name="bob12.bobby@computecanada.ca",
        given_name="Bob",
        surname="Rodriguez",
        mail="bob-rodriguez435@example.com",
        ssh_public_key="ssh-rsa FAKE",
    )


@pytest.fixture
def admin() -> Callable[[sqlite3.Connection], SAMLUser]:
    return SAMLUser(
        orm=None,
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
        "empty.calculquebec.cloud",
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
