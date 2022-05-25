import pytest

from mchub.models.magic_castle.magic_castle import MagicCastle
from mchub.configuration.cloud import DEFAULT_CLOUD
from mchub.models.magic_castle.cluster_status_code import ClusterStatusCode
from mchub.exceptions.invalid_usage_exception import ClusterNotFoundException

from ...test_helpers import *  # noqa
from ...mocks.configuration.config_mock import config_auth_saml_mock  # noqa;


def test_full_name(alice, bob, admin):
    assert alice.full_name == "Alice Tremblay"
    assert bob.full_name == "Bob Rodriguez"
    assert admin.full_name == "Admin Istrator"


def test_query_magic_castles(alice, bob, admin):
    # Alice
    alice_magic_castles = alice.query_magic_castles()
    assert [magic_castle.hostname for magic_castle in alice_magic_castles] == [
        "buildplanning.calculquebec.cloud",
        "created.calculquebec.cloud",
        "valid1.calculquebec.cloud",
    ]
    assert [magic_castle.status for magic_castle in alice_magic_castles] == [
        ClusterStatusCode.PLAN_RUNNING,
        ClusterStatusCode.CREATED,
        ClusterStatusCode.PROVISIONING_SUCCESS,
    ]

    # Bob
    bob_magic_castles = bob.query_magic_castles()
    assert [magic_castle.hostname for magic_castle in bob_magic_castles] == [
        "empty.calculquebec.cloud",
        "empty-state.calculquebec.cloud",
        "missingfloatingips.c3.ca",
        "missingnodes.c3.ca",
    ]
    assert [magic_castle.status for magic_castle in bob_magic_castles] == [
        ClusterStatusCode.BUILD_ERROR,
        ClusterStatusCode.BUILD_ERROR,
        ClusterStatusCode.BUILD_RUNNING,
        ClusterStatusCode.BUILD_ERROR,
    ]

    # Admin
    admin_magic_castles = admin.query_magic_castles()
    assert [magic_castle.hostname for magic_castle in admin_magic_castles] == [
        "buildplanning.calculquebec.cloud",
        "created.calculquebec.cloud",
        "empty-state.calculquebec.cloud",
        "empty.calculquebec.cloud",
        "missingfloatingips.c3.ca",
        "missingnodes.c3.ca",
        "noowner.calculquebec.cloud",
        "valid1.calculquebec.cloud",
    ]
    assert [magic_castle.status for magic_castle in admin_magic_castles] == [
        ClusterStatusCode.PLAN_RUNNING,
        ClusterStatusCode.CREATED,
        ClusterStatusCode.BUILD_ERROR,
        ClusterStatusCode.BUILD_ERROR,
        ClusterStatusCode.BUILD_RUNNING,
        ClusterStatusCode.BUILD_ERROR,
        ClusterStatusCode.PROVISIONING_SUCCESS,
        ClusterStatusCode.PROVISIONING_SUCCESS,
    ]


@pytest.mark.usefixtures("fake_successful_subprocess_run")
def test_create_empty_magic_castle(alice):
    user = alice
    magic_castle = user.create_empty_magic_castle()
    magic_castle.plan_creation(
        {
            "cloud_id": DEFAULT_CLOUD,
            "cluster_name": "alice123",
            "domain": "c3.ca",
            "image": "CentOS-7-x64-2021-11",
            "nb_users": 10,
            "instances": {
                "mgmt": {
                    "type": "p4-6gb",
                    "count": 1,
                    "tags": ["mgmt", "nfs", "puppet"],
                },
                "login": {
                    "type": "p4-6gb",
                    "count": 1,
                    "tags": ["login", "proxy", "public"],
                },
                "node": {"type": "p2-3gb", "count": 1, "tags": ["node"]},
            },
            "volumes": {
                "nfs": {
                    "home": {"size": 100},
                    "project": {"size": 50},
                    "scratch": {"size": 50},
                }
            },
            "public_keys": ["ssh-rsa FAKE"],
            "guest_passwd": "",
        }
    )
    magic_castle2 = MagicCastle("alice123.c3.ca")
    assert magic_castle2.hostname == "alice123.c3.ca"
    assert magic_castle2.status.value == "created"
    assert magic_castle2.get_plan_type().value == "build"
    assert magic_castle2.owner.id == "alice@computecanada.ca"


def test_query_magic_castles(alice):
    magic_castle = alice.query_magic_castles(hostname="valid1.calculquebec.cloud")[0]
    assert magic_castle.hostname == "valid1.calculquebec.cloud"
    assert magic_castle.owner.id == "alice@computecanada.ca"
    assert magic_castle.status == ClusterStatusCode.PROVISIONING_SUCCESS


def test_query_magic_castles_admin(admin):
    magic_castle = admin.query_magic_castles(hostname="valid1.calculquebec.cloud")[0]
    assert magic_castle.hostname == "valid1.calculquebec.cloud"
    assert magic_castle.owner.id == "alice@computecanada.ca"
    assert magic_castle.status == ClusterStatusCode.PROVISIONING_SUCCESS


def test_query_magic_castles_unauthorized_user(bob):
    with pytest.raises(ClusterNotFoundException):
        bob.query_magic_castles(hostname="valid1.calculquebec.cloud")[0]
    with pytest.raises(ClusterNotFoundException):
        bob.query_magic_castles(hostname="noowner.calculquebec.cloud")
