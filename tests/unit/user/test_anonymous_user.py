import pytest

from mchub.constants import DEFAULT_CLOUD
from mchub.models.user.anonymous_user import AnonymousUser
from mchub.models.magic_castle.cluster_status_code import ClusterStatusCode

from ... test_helpers import *  # noqa
from ... mocks.configuration.config_mock import config_auth_saml_mock  # noqa;


def test_full_name(database_connection):
    assert AnonymousUser(database_connection).full_name == None


def test_get_all_magic_castles(database_connection):
    all_magic_castles = AnonymousUser(database_connection).get_all_magic_castles()
    assert [magic_castle.hostname for magic_castle in all_magic_castles] == [
        "buildplanning.calculquebec.cloud",
        "created.calculquebec.cloud",
        "empty-state.calculquebec.cloud",
        "empty.calculquebec.cloud",
        "missingfloatingips.c3.ca",
        "missingnodes.sub.example.com",
        "noowner.calculquebec.cloud",
        "valid1.calculquebec.cloud",
    ]
    assert [magic_castle.status for magic_castle in all_magic_castles] == [
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
def test_create_empty_magic_castle(database_connection):
    user = AnonymousUser(database_connection)
    magic_castle = user.create_empty_magic_castle()
    magic_castle.plan_creation(
        {
            "cloud_id": DEFAULT_CLOUD,
            "cluster_name": "anon123",
            "domain": "sub.example.com",
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
    result = database_connection.execute(
        "SELECT hostname, status, plan_type, owner FROM magic_castles WHERE hostname=?",
        ("anon123.sub.example.com",),
    ).fetchall()
    assert result == [
        (
            "anon123.sub.example.com",
            "created",
            "build",
            None,
        )
    ]


def test_get_magic_castle_by_hostname(database_connection):
    user = AnonymousUser(database_connection)
    magic_castle = user.get_magic_castle_by_hostname("valid1.calculquebec.cloud")
    assert magic_castle.hostname == "valid1.calculquebec.cloud"
    assert magic_castle.owner.id == "alice@computecanada.ca"
    assert magic_castle.status == ClusterStatusCode.PROVISIONING_SUCCESS
