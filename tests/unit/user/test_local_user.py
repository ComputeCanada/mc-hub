import pytest

from mchub.models.magic_castle.magic_castle import MagicCastle
from mchub.configuration.cloud import DEFAULT_CLOUD
from mchub.models.user import LocalUser
from mchub.models.magic_castle.cluster_status_code import ClusterStatusCode

from ...test_helpers import *  # noqa
from ...mocks.configuration.config_mock import config_auth_saml_mock  # noqa;


def test_full_name():
    assert LocalUser().full_name == None


def test_query_magic_castles():
    all_magic_castles = LocalUser().query_magic_castles()
    assert [magic_castle.hostname for magic_castle in all_magic_castles] == [
        "buildplanning.calculquebec.cloud",
        "created.calculquebec.cloud",
        "empty-state.calculquebec.cloud",
        "empty.calculquebec.cloud",
        "missingfloatingips.c3.ca",
        "missingnodes.c3.ca",
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
def test_create_empty_magic_castle(client):
    client.get("/api/user/me")
    user = LocalUser()
    magic_castle = user.create_empty_magic_castle()
    magic_castle.plan_creation(
        {
            "cloud_id": DEFAULT_CLOUD,
            "cluster_name": "anon123",
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
    magic_castle2 = user.query_magic_castles(hostname="anon123.c3.ca")[0]
    assert magic_castle2.hostname == "anon123.c3.ca"
    assert magic_castle2.status == ClusterStatusCode.CREATED
    assert magic_castle2.plan_type == PlanType.BUILD
    assert magic_castle2.owner == None


def test_query_magic_castles(client):
    client.get("/api/user/me")
    user = LocalUser()
    magic_castle = user.query_magic_castles(hostname="valid1.calculquebec.cloud")[0]
    assert magic_castle.hostname == "valid1.calculquebec.cloud"
    assert magic_castle.owner == "alice@computecanada.ca"
    assert magic_castle.status == ClusterStatusCode.PROVISIONING_SUCCESS