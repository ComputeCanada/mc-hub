from mchub.models.magic_castle.cluster_status_code import ClusterStatusCode

from ..test_helpers import *
from ..mocks.configuration.config_mock import config_auth_none_mock  # noqa;
from subprocess import getoutput
from getpass import getuser

from ..data import (
    NON_EXISTING_CLUSTER_CONFIGURATION,
    EXISTING_CLUSTER_CONFIGURATION,
    IGNORE_FIELDS,
    EXISTING_HOSTNAME,
    NON_EXISTING_HOSTNAME,
    EXISTING_CLUSTER_STATE,
    CLUSTERS,
    PROGRESS_DATA,
)

# GET /api/users/me
def test_get_current_user(client):
    res = client.get(f"/api/users/me")
    assert res.get_json() == {
        "username": getuser(),
        "public_keys": getoutput("ssh-add -L").split("\n"),
        "usertype": "local",
    }


# GET /api/magic_castle
def test_get_all_magic_castle_names(client):
    res = client.get(f"/api/magic-castles")
    results = {}
    for result in res.get_json():
        for field in IGNORE_FIELDS:
            result.pop(field)
        results[result["hostname"]] = result

    assert (
        results["buildplanning.calculquebec.cloud"]
        == CLUSTERS["buildplanning.calculquebec.cloud"]
    )
    assert (
        results["created.calculquebec.cloud"] == CLUSTERS["created.calculquebec.cloud"]
    )
    assert results["valid1.calculquebec.cloud"] == CLUSTERS["valid1.calculquebec.cloud"]
    assert (
        results["empty-state.calculquebec.cloud"]
        == CLUSTERS["empty-state.calculquebec.cloud"]
    )
    assert results["empty.calculquebec.cloud"] == CLUSTERS["empty.calculquebec.cloud"]
    assert results["missingfloatingips.c3.ca"] == CLUSTERS["missingfloatingips.c3.ca"]
    assert results["missingnodes.c3.ca"] == CLUSTERS["missingnodes.c3.ca"]
    assert (
        results["noowner.calculquebec.cloud"] == CLUSTERS["noowner.calculquebec.cloud"]
    )
    assert res.status_code == 200


# GET /api/magic-castles/<hostname>
def test_get_state_existing(client):
    res = client.get(f"/api/magic-castles/{EXISTING_HOSTNAME}")
    state = res.get_json()
    for field in IGNORE_FIELDS:
        state.pop(field)
    assert state == EXISTING_CLUSTER_STATE
    assert res.status_code == 200


def test_get_state_non_existing(client):
    res = client.get(f"/api/magic-castles/{NON_EXISTING_HOSTNAME}")
    assert res.get_json() == {"message": "This cluster does not exist."}
    assert res.status_code != 200


# GET /api/magic-castles/<hostname>/status
@pytest.mark.skip(reason="source of truth is currently false")
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
