from pickle import NONE
import pytest
import sqlite3

from pathlib import Path
from os import path
from shutil import rmtree, copytree
from typing import Callable

from mchub import create_app
from mchub.database import db
from mchub.configuration.cloud import DEFAULT_CLOUD
from mchub.models.user import SAMLUser
from mchub.models.magic_castle.magic_castle import MagicCastleORM
from mchub.models.magic_castle.cluster_status_code import ClusterStatusCode
from mchub.models.magic_castle.plan_type import PlanType

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
        # Using an in-memory database for faster unit tests with less disk IO

        buildplanning = MagicCastleORM(
            hostname="buildplanning.calculquebec.cloud",
            plan_type=PlanType.BUILD,
            status=ClusterStatusCode.PLAN_RUNNING,
            owner="alice@computecanada.ca",
            expiration_date="2029-01-01",
            cloud_id=DEFAULT_CLOUD,
        )
        created = MagicCastleORM(
            hostname="created.calculquebec.cloud",
            status=ClusterStatusCode.CREATED,
            plan_type=PlanType.BUILD,
            owner="alice@computecanada.ca",
            expiration_date="2029-01-01",
            cloud_id=DEFAULT_CLOUD,
        )
        empty_state = MagicCastleORM(
            hostname="empty-state.calculquebec.cloud",
            status=ClusterStatusCode.BUILD_ERROR,
            plan_type=PlanType.NONE,
            owner="bob12.bobby@computecanada.ca",
            expiration_date="2029-01-01",
            cloud_id=DEFAULT_CLOUD,
        )
        empty = MagicCastleORM(
            hostname="empty.calculquebec.cloud",
            status=ClusterStatusCode.BUILD_ERROR,
            plan_type=PlanType.NONE,
            owner="bob12.bobby@computecanada.ca",
            expiration_date="2029-01-01",
            cloud_id=DEFAULT_CLOUD,
        )
        missingfip = MagicCastleORM(
            hostname="missingfloatingips.c3.ca",
            status=ClusterStatusCode.BUILD_RUNNING,
            plan_type=PlanType.NONE,
            owner="bob12.bobby@computecanada.ca",
            expiration_date="2029-01-01",
            cloud_id=DEFAULT_CLOUD,
        )
        missingnodes = MagicCastleORM(
            hostname="missingnodes.c3.ca",
            status=ClusterStatusCode.BUILD_ERROR,
            plan_type=PlanType.NONE,
            owner="bob12.bobby@computecanada.ca",
            expiration_date="2029-01-01",
            cloud_id=DEFAULT_CLOUD,
        )
        valid1 = MagicCastleORM(
            hostname="valid1.calculquebec.cloud",
            status=ClusterStatusCode.PROVISIONING_SUCCESS,
            plan_type=PlanType.DESTROY,
            owner="alice@computecanada.ca",
            expiration_date="2029-01-01",
            cloud_id=DEFAULT_CLOUD,
        )
        noower = MagicCastleORM(
            hostname="noowner.calculquebec.cloud",
            status=ClusterStatusCode.PROVISIONING_SUCCESS,
            plan_type=PlanType.DESTROY,
            expiration_date="2029-01-01",
            cloud_id=DEFAULT_CLOUD,
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
        edu_person_principal_name="alice@computecanada.ca",
        given_name="Alice",
        surname="Tremblay",
        mail="alice.tremblay@example.com",
        ssh_public_key="ssh-rsa FAKE",
    )


@pytest.fixture
def bob() -> Callable[[sqlite3.Connection], SAMLUser]:
    return SAMLUser(
        edu_person_principal_name="bob12.bobby@computecanada.ca",
        given_name="Bob",
        surname="Rodriguez",
        mail="bob-rodriguez435@example.com",
        ssh_public_key="ssh-rsa FAKE",
    )


@pytest.fixture
def admin() -> Callable[[sqlite3.Connection], SAMLUser]:
    return SAMLUser(
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
    mocker.patch("mchub.models.magic_castle.magic_castle.run", return_value=None)
