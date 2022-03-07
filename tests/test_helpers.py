import pytest
import sqlite3

from pathlib import Path
from os import path
from shutil import rmtree, copytree
from typing import Callable


from mchub.configuration.cloud import DEFAULT_CLOUD
from mchub.database.schema_manager import SchemaManager
from mchub.database.database_manager import DatabaseManager
from mchub.models.user.authenticated_user import AuthenticatedUser

from . mocks.openstack.openstack_connection_mock import OpenStackConnectionMock

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


@pytest.fixture(autouse=True)
def database_connection(mocker):
    # Using an in-memory database for faster unit tests with less disk IO
    mocker.patch("mchub.database.database_manager.DATABASE_FILE_PATH", new=":memory:")

    with DatabaseManager.connect() as database_connection:
        # The database :memory: only exist within a single connection.
        # Therefore, the DatabaseConnection object is mocked to always return the same connection.
        class MockDatabaseConnection:
            def __init__(self):
                self.__connection = None

            def __enter__(self) -> sqlite3.Connection:
                return database_connection

            def __exit__(self, type, value, traceback):
                pass

        mocker.patch(
            "mchub.database.database_manager.DatabaseManager.connect",
            return_value=MockDatabaseConnection(),
        )

        # Creating the DB schema
        SchemaManager(database_connection).update_schema()

        # Seeding test data
        test_magic_castle_rows_with_owner = [
            (
                "buildplanning.calculquebec.cloud",
                "plan_running",
                "build",
                "alice@computecanada.ca",
                "2029-01-01",
                DEFAULT_CLOUD,
            ),
            (
                "created.calculquebec.cloud",
                "created",
                "build",
                "alice@computecanada.ca",
                "2029-01-01",
                DEFAULT_CLOUD,
            ),
            (
                "empty.calculquebec.cloud",
                "build_error",
                "none",
                "bob12.bobby@computecanada.ca",
                "2029-01-01",
                DEFAULT_CLOUD,
            ),
            (
                "empty-state.calculquebec.cloud",
                "build_error",
                "none",
                "bob12.bobby@computecanada.ca",
                "2029-01-01",
                DEFAULT_CLOUD,
            ),
            (
                "missingfloatingips.c3.ca",
                "build_running",
                "none",
                "bob12.bobby@computecanada.ca",
                "2029-01-01",
                DEFAULT_CLOUD,
            ),
            (
                "missingnodes.sub.example.com",
                "build_error",
                "none",
                "bob12.bobby@computecanada.ca",
                "2029-01-01",
                DEFAULT_CLOUD,
            ),
            (
                "valid1.calculquebec.cloud",
                "provisioning_success",
                "destroy",
                "alice@computecanada.ca",
                "2029-01-01",
                DEFAULT_CLOUD,
            ),
        ]
        test_magic_castle_rows_without_owner = [
            (
                "noowner.calculquebec.cloud",
                "provisioning_success",
                "destroy",
                "2029-01-01",
                DEFAULT_CLOUD,
            ),
        ]
        database_connection.executemany(
            "INSERT INTO magic_castles (hostname, status, plan_type, owner, expiration_date, cloud_id) values (?, ?, ?, ?, ?, ?)",
            test_magic_castle_rows_with_owner,
        )
        database_connection.executemany(
            "INSERT INTO magic_castles (hostname, status, plan_type, expiration_date, cloud_id) values (?, ?, ?, ?, ?)",
            test_magic_castle_rows_without_owner,
        )

        database_connection.commit()
        yield database_connection


@pytest.fixture
def alice() -> Callable[[sqlite3.Connection], AuthenticatedUser]:
    return lambda database_connection: AuthenticatedUser(
        database_connection,
        edu_person_principal_name="alice@computecanada.ca",
        given_name="Alice",
        surname="Tremblay",
        mail="alice.tremblay@example.com",
        ssh_public_key="ssh-rsa FAKE",
    )


@pytest.fixture
def bob() -> Callable[[sqlite3.Connection], AuthenticatedUser]:
    return lambda database_connection: AuthenticatedUser(
        database_connection,
        edu_person_principal_name="bob12.bobby@computecanada.ca",
        given_name="Bob",
        surname="Rodriguez",
        mail="bob-rodriguez435@example.com",
        ssh_public_key="ssh-rsa FAKE",
    )


@pytest.fixture
def admin() -> Callable[[sqlite3.Connection], AuthenticatedUser]:
    return lambda database_connection: AuthenticatedUser(
        database_connection,
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
        "missingnodes.sub.example.com",
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
