import pytest

from mchub.models.magic_castle.magic_castle import MagicCastle
from mchub.models.user import LocalUser
from mchub.models.magic_castle.cluster_status_code import ClusterStatusCode

from ...test_helpers import *  # noqa
from ...mocks.configuration.config_mock import config_auth_none_mock  # noqa;


def test_query_magic_castles(app):
    all_magic_castles = LocalUser().magic_castles
    assert [magic_castle.hostname for magic_castle in all_magic_castles] == [
        "buildplanning.magic-castle.cloud",
        "created.magic-castle.cloud",
        "empty-state.magic-castle.cloud",
        "missingfloatingips.mc.ca",
        "missingnodes.mc.ca",
        "noowner.magic-castle.cloud",
        "valid1.magic-castle.cloud",
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
def test_create_empty_magic_castle(app):
    magic_castle = MagicCastle()
    magic_castle.plan_creation(
        {
            "cloud": {"id": 1, "name": "test-project"},
            "cluster_name": "anon123",
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

    data = MagicCastleORM.query.get(magic_castle.orm.id)
    assert data.status == ClusterStatusCode.CREATED


def test_query_magic_castles(app):
    orm = MagicCastleORM.query.filter_by(hostname="valid1.magic-castle.cloud").first()
    assert orm.status == ClusterStatusCode.PROVISIONING_SUCCESS
