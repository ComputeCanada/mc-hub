from models.magic_castle.cluster_status_code import ClusterStatusCode
from exceptions.invalid_usage_exception import ClusterNotFoundException
from tests.test_helpers import *  # noqa
import pytest
from tests.mocks.configuration.config_mock import config_auth_saml_mock  # noqa;


def test_full_name(database_connection, alice, bob, admin):
    assert alice(database_connection).full_name == "Alice Tremblay"
    assert bob(database_connection).full_name == "Bob Rodriguez"
    assert admin(database_connection).full_name == "Admin Istrator"


def test_get_all_magic_castles(database_connection, alice, bob, admin):
    # Alice
    alice_magic_castles = alice(database_connection).get_all_magic_castles()
    assert [magic_castle.get_hostname() for magic_castle in alice_magic_castles] == [
        "buildplanning.calculquebec.cloud",
        "created.calculquebec.cloud",
        "valid1.calculquebec.cloud",
    ]
    assert [magic_castle.get_status() for magic_castle in alice_magic_castles] == [
        ClusterStatusCode.PLAN_RUNNING,
        ClusterStatusCode.CREATED,
        ClusterStatusCode.PROVISIONING_SUCCESS,
    ]

    # Bob
    bob_magic_castles = bob(database_connection).get_all_magic_castles()
    assert [magic_castle.get_hostname() for magic_castle in bob_magic_castles] == [
        "empty.calculquebec.cloud",
        "missingfloatingips.c3.ca",
        "missingnodes.sub.example.com",
    ]
    assert [magic_castle.get_status() for magic_castle in bob_magic_castles] == [
        ClusterStatusCode.BUILD_ERROR,
        ClusterStatusCode.BUILD_RUNNING,
        ClusterStatusCode.BUILD_ERROR,
    ]

    # Admin
    admin_magic_castles = admin(database_connection).get_all_magic_castles()
    assert [magic_castle.get_hostname() for magic_castle in admin_magic_castles] == [
        "buildplanning.calculquebec.cloud",
        "created.calculquebec.cloud",
        "empty.calculquebec.cloud",
        "missingfloatingips.c3.ca",
        "missingnodes.sub.example.com",
        "valid1.calculquebec.cloud",
        "noowner.calculquebec.cloud",
    ]
    assert [magic_castle.get_status() for magic_castle in admin_magic_castles] == [
        ClusterStatusCode.PLAN_RUNNING,
        ClusterStatusCode.CREATED,
        ClusterStatusCode.BUILD_ERROR,
        ClusterStatusCode.BUILD_RUNNING,
        ClusterStatusCode.BUILD_ERROR,
        ClusterStatusCode.PROVISIONING_SUCCESS,
        ClusterStatusCode.PROVISIONING_SUCCESS,
    ]


@pytest.mark.usefixtures("fake_successful_subprocess_run")
def test_create_empty_magic_castle(database_connection, alice):
    user = alice(database_connection)
    magic_castle = user.create_empty_magic_castle()
    magic_castle.set_configuration(
        {
            "cluster_name": "alice123",
            "domain": "sub.example.com",
            "image": "CentOS-7-x64-2019-07",
            "nb_users": 10,
            "instances": {
                "mgmt": {"type": "p4-6gb", "count": 1},
                "login": {"type": "p4-6gb", "count": 1},
                "node": {"type": "p2-3gb", "count": 1},
            },
            "storage": {
                "type": "nfs",
                "home_size": 100,
                "project_size": 50,
                "scratch_size": 50,
            },
            "public_keys": [],
            "guest_passwd": "",
            "os_floating_ips": [],
        }
    )
    magic_castle.plan_creation()
    result = database_connection.execute(
        "SELECT hostname, cluster_name, domain, status, plan_type, owner FROM magic_castles WHERE hostname=?",
        ("alice123.sub.example.com",),
    ).fetchall()
    assert result == [
        (
            "alice123.sub.example.com",
            "alice123",
            "sub.example.com",
            "created",
            "build",
            "alice@computecanada.ca",
        )
    ]


def test_get_magic_castle_by_hostname(database_connection, alice):
    user = alice(database_connection)
    magic_castle = user.get_magic_castle_by_hostname("valid1.calculquebec.cloud")
    assert magic_castle.get_hostname() == "valid1.calculquebec.cloud"
    assert magic_castle.get_owner() == "alice@computecanada.ca"
    assert magic_castle.get_status() == ClusterStatusCode.PROVISIONING_SUCCESS


def test_get_magic_castle_by_hostname_admin(database_connection, admin):
    user = admin(database_connection)
    magic_castle = user.get_magic_castle_by_hostname("valid1.calculquebec.cloud")
    assert magic_castle.get_hostname() == "valid1.calculquebec.cloud"
    assert magic_castle.get_owner() == "alice@computecanada.ca"
    assert magic_castle.get_status() == ClusterStatusCode.PROVISIONING_SUCCESS


def test_get_magic_castle_by_hostname_unauthorized_user(database_connection, bob):
    user = bob(database_connection)
    with pytest.raises(ClusterNotFoundException):
        user.get_magic_castle_by_hostname("valid1.calculquebec.cloud")
    with pytest.raises(ClusterNotFoundException):
        user.get_magic_castle_by_hostname("noowner.calculquebec.cloud")
