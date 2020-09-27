from models.user.anonymous_user import AnonymousUser
from models.magic_castle.cluster_status_code import ClusterStatusCode
from tests.test_helpers import *
from tests.mocks.configuration.config_mock import config_auth_saml_mock


def test_full_name(database_connection):
    assert AnonymousUser(database_connection).full_name == None


def test_get_all_magic_castles(database_connection):
    all_magic_castles = AnonymousUser(database_connection).get_all_magic_castles()
    assert [magic_castle.get_hostname() for magic_castle in all_magic_castles] == [
        "buildplanning.calculquebec.cloud",
        "created.calculquebec.cloud",
        "empty.calculquebec.cloud",
        "missingfloatingips.c3.ca",
        "missingnodes.sub.example.com",
        "noowner.calculquebec.cloud",
        "valid1.calculquebec.cloud",
    ]
    assert [magic_castle.get_status() for magic_castle in all_magic_castles] == [
        ClusterStatusCode.PLAN_RUNNING,
        ClusterStatusCode.CREATED,
        ClusterStatusCode.BUILD_ERROR,
        ClusterStatusCode.BUILD_RUNNING,
        ClusterStatusCode.BUILD_ERROR,
        ClusterStatusCode.PROVISIONING_SUCCESS,
        ClusterStatusCode.PROVISIONING_SUCCESS,
    ]


def test_create_empty_magic_castle(database_connection):
    user = AnonymousUser(database_connection)
    magic_castle = user.create_empty_magic_castle()
    magic_castle.load_configuration(
        {
            "cluster_name": "anon123",
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
        ("anon123.sub.example.com",),
    ).fetchall()
    assert result == [
        (
            "anon123.sub.example.com",
            "anon123",
            "sub.example.com",
            "created",
            "build",
            None,
        )
    ]


def test_get_magic_castle_by_hostname(database_connection):
    user = AnonymousUser(database_connection)
    magic_castle = user.get_magic_castle_by_hostname("valid1.calculquebec.cloud")
    assert magic_castle.get_hostname() == "valid1.calculquebec.cloud"
    assert magic_castle.get_owner() == "alice@computecanada.ca"
    assert magic_castle.get_status() == ClusterStatusCode.PROVISIONING_SUCCESS
