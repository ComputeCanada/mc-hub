import pytest

from ...test_helpers import (
    app,
    client,
    generate_test_clusters,
    mock_clusters_path,
    alice,
    bob,
    admin,
    fake_successful_subprocess_run,
)  # noqa

from ...mocks.configuration.config_mock import (
    config_auth_saml_mock as config_mock,
)  # noqa;


def test_query_magic_castles_alice(alice):
    from mchub.models.magic_castle.cluster_status_code import ClusterStatusCode

    # Alice
    alice_magic_castles = alice.magic_castles
    assert [magic_castle.hostname for magic_castle in alice_magic_castles] == [
        "buildplanning.magic-castle.cloud",
        "created.magic-castle.cloud",
        "valid1.magic-castle.cloud",
    ]
    assert [magic_castle.status for magic_castle in alice_magic_castles] == [
        ClusterStatusCode.PLAN_RUNNING,
        ClusterStatusCode.CREATED,
        ClusterStatusCode.PROVISIONING_SUCCESS,
    ]


def test_query_magic_castles_bob(bob):
    from mchub.models.magic_castle.cluster_status_code import ClusterStatusCode

    # Bob
    bob_magic_castles = bob.magic_castles
    assert [magic_castle.hostname for magic_castle in bob_magic_castles] == [
        "empty-state.magic-castle.cloud",
        "missingfloatingips.mc.ca",
        "missingnodes.mc.ca",
        "noowner.magic-castle.cloud",
    ]
    assert [magic_castle.status for magic_castle in bob_magic_castles] == [
        ClusterStatusCode.BUILD_ERROR,
        ClusterStatusCode.BUILD_RUNNING,
        ClusterStatusCode.BUILD_ERROR,
        ClusterStatusCode.PROVISIONING_SUCCESS,
    ]


def test_query_magic_castles_admin(admin):
    from mchub.models.magic_castle.cluster_status_code import ClusterStatusCode

    # Admin
    admin_magic_castles = admin.magic_castles
    assert [magic_castle.hostname for magic_castle in admin_magic_castles] == [
        "buildplanning.magic-castle.cloud",
        "created.magic-castle.cloud",
        "valid1.magic-castle.cloud",
        "empty-state.magic-castle.cloud",
        "missingfloatingips.mc.ca",
        "missingnodes.mc.ca",
        "noowner.magic-castle.cloud",
    ]
    assert [magic_castle.status for magic_castle in admin_magic_castles] == [
        ClusterStatusCode.PLAN_RUNNING,
        ClusterStatusCode.CREATED,
        ClusterStatusCode.PROVISIONING_SUCCESS,
        ClusterStatusCode.BUILD_ERROR,
        ClusterStatusCode.BUILD_RUNNING,
        ClusterStatusCode.BUILD_ERROR,
        ClusterStatusCode.PROVISIONING_SUCCESS,
    ]


@pytest.mark.usefixtures("fake_successful_subprocess_run")
def test_create_empty_magic_castle(alice):
    from mchub.models.magic_castle.magic_castle import MagicCastle
    from mchub.models.magic_castle.cluster_status_code import ClusterStatusCode
    from mchub.models.magic_castle.plan_type import PlanType

    magic_castle = MagicCastle()
    magic_castle.plan_creation(
        {
            "cloud": {"id": 1, "name": "test-project"},
            "cluster_name": "alice123",
            "domain": "mc.ca",
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
    magic_castle2 = alice.magic_castles[-1]
    assert magic_castle2.hostname == "alice123.mc.ca"
    assert magic_castle2.status == ClusterStatusCode.CREATED
    assert magic_castle2.plan_type == PlanType.BUILD
