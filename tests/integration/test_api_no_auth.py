from mchub.models.magic_castle.cluster_status_code import ClusterStatusCode

from ..test_helpers import *
from ..mocks.configuration.config_mock import config_auth_none_mock  # noqa;
from subprocess import getoutput
from getpass import getuser

from ..data import (
    NON_EXISTING_CLUSTER_CONFIGURATION,
    EXISTING_CLUSTER_CONFIGURATION,
    EXISTING_HOSTNAME,
    NON_EXISTING_HOSTNAME,
    EXISTING_CLUSTER_STATE,
    CLUSTERS,
    PROGRESS_DATA,
    DEFAULT_TEMPLATE,
)

# GET /api/users/me
def test_get_current_user(client):
    res = client.get(f"/api/users/me")
    assert res.get_json() == {
        "username": getuser(),
        "public_keys": getoutput("ssh-add -L").split("\n"),
        "usertype": "local",
    }


def test_get_current_user(client):
    res = client.get(f"/api/template/default")
    assert res.get_json() == DEFAULT_TEMPLATE


# GET /api/magic_castle
def test_get_all_magic_castle_names(client):
    res = client.get(f"/api/magic-castles")
    assert res.status_code == 200
    for result in res.get_json():
        cluster_name = result["hostname"]
        assert result == CLUSTERS[cluster_name]


# GET /api/magic-castles/<hostname>
def test_get_state_existing(client):
    res = client.get(f"/api/magic-castles/{EXISTING_HOSTNAME}")
    state = res.get_json()
    assert state == EXISTING_CLUSTER_STATE
    assert res.status_code == 200


def test_get_state_non_existing(client):
    res = client.get(f"/api/magic-castles/{NON_EXISTING_HOSTNAME}")
    assert res.get_json() == {"message": "This cluster does not exist."}
    assert res.status_code != 200


# GET /api/magic-castles/<hostname>/status
def test_get_status(mocker, client):
    res = client.get(f"/api/magic-castles/missingfloatingips.c3.ca/status")
    assert res.get_json() == PROGRESS_DATA


def test_get_status_code(client):
    res = client.get(f"/api/magic-castles/{NON_EXISTING_HOSTNAME}/status")
    assert res.get_json()["status"] == "not_found"

    orm = MagicCastleORM.query.filter_by(hostname=EXISTING_HOSTNAME).first()
    orm.status = ClusterStatusCode.BUILD_RUNNING
    db.session.commit()
    res = client.get(f"/api/magic-castles/{EXISTING_HOSTNAME}/status")
    assert res.get_json()["status"] == "build_running"

    orm = MagicCastleORM.query.filter_by(hostname=EXISTING_HOSTNAME).first()
    orm.status = ClusterStatusCode.PROVISIONING_SUCCESS
    db.session.commit()
    res = client.get(f"/api/magic-castles/{EXISTING_HOSTNAME}/status")
    assert res.get_json()["status"] == "provisioning_success"

    orm = MagicCastleORM.query.filter_by(hostname=EXISTING_HOSTNAME).first()
    orm.status = ClusterStatusCode.BUILD_ERROR
    db.session.commit()
    res = client.get(f"/api/magic-castles/{EXISTING_HOSTNAME}/status")
    assert res.get_json()["status"] == "build_error"

    orm = MagicCastleORM.query.filter_by(hostname=EXISTING_HOSTNAME).first()
    orm.status = ClusterStatusCode.DESTROY_RUNNING
    db.session.commit()
    res = client.get(f"/api/magic-castles/{EXISTING_HOSTNAME}/status")
    assert res.get_json()["status"] == "destroy_running"

    orm = MagicCastleORM.query.filter_by(hostname=EXISTING_HOSTNAME).first()
    orm.status = ClusterStatusCode.DESTROY_ERROR
    db.session.commit()
    res = client.get(f"/api/magic-castles/{EXISTING_HOSTNAME}/status")
    assert res.get_json()["status"] == "destroy_error"


# DELETE /api/magic-castles/<hostname>
def test_delete_invalid_status(client):
    res = client.delete(f"/api/magic-castles/{NON_EXISTING_HOSTNAME}")
    assert res.get_json() == {"message": "This cluster does not exist."}
    assert res.status_code != 200

    orm = MagicCastleORM.query.filter_by(hostname=EXISTING_HOSTNAME).first()
    orm.status = ClusterStatusCode.DESTROY_RUNNING
    db.session.commit()
    res = client.delete(f"/api/magic-castles/{EXISTING_HOSTNAME}")
    assert res.get_json() == {"message": "This cluster is busy."}
    assert res.status_code != 200

    orm = MagicCastleORM.query.filter_by(hostname=EXISTING_HOSTNAME).first()
    orm.status = ClusterStatusCode.BUILD_RUNNING
    db.session.commit()
    res = client.delete(f"/api/magic-castles/{EXISTING_HOSTNAME}")
    assert res.get_json() == {"message": "This cluster is busy."}
    assert res.status_code != 200


# PUT /api/magic-castles/<hostname>
def test_modify_invalid_status(client):
    res = client.put(
        f"/api/magic-castles/{NON_EXISTING_HOSTNAME}",
        json=NON_EXISTING_CLUSTER_CONFIGURATION,
    )
    assert res.get_json() == {"message": "This cluster does not exist."}
    assert res.status_code != 200

    orm = MagicCastleORM.query.filter_by(hostname=EXISTING_HOSTNAME).first()
    orm.status = ClusterStatusCode.BUILD_RUNNING
    db.session.commit()
    res = client.put(
        f"/api/magic-castles/{EXISTING_HOSTNAME}",
        json=EXISTING_CLUSTER_CONFIGURATION,
    )
    assert res.get_json() == {"message": "This cluster is busy."}
    assert res.status_code != 200

    orm = MagicCastleORM.query.filter_by(hostname=EXISTING_HOSTNAME).first()
    orm.status = ClusterStatusCode.DESTROY_RUNNING
    db.session.commit()
    res = client.put(
        f"/api/magic-castles/{EXISTING_HOSTNAME}",
        json=EXISTING_CLUSTER_CONFIGURATION,
    )
    assert res.get_json() == {"message": "This cluster is busy."}
    assert res.status_code != 200
