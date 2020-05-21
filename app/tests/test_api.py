from server import app
import pytest

NON_EXISTING_CLUSTER_NAME = "non-existing"
VALID_MAGIC_CASTLE_CONFIGURATION = {
    "cluster_name": "valid-cluster",
    "domain": "calculquebec.cloud",
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


@pytest.fixture
def client():
    app.config["TESTING"] = True

    with app.test_client() as client:
        yield client


def test_get_state_non_existing(client):
    res = client.get(f"/api/magic-castle/{NON_EXISTING_CLUSTER_NAME}")
    assert res.get_json() == {"message": "This cluster is not fully built yet"}
    assert res.status_code != 200


def test_get_status_non_existing(client):
    res = client.get(f"/api/magic-castle/{NON_EXISTING_CLUSTER_NAME}/status")
    assert res.get_json() == {"status": "not_found"}


def test_delete_non_existing(client):
    res = client.delete(f"/api/magic-castle/{NON_EXISTING_CLUSTER_NAME}")
    assert res.get_json() == {"message": "This cluster is not fully built yet"}
    assert res.status_code != 200


def test_modify_non_existing(client):
    res = client.put(
        f"/api/magic-castle/{NON_EXISTING_CLUSTER_NAME}",
        json=VALID_MAGIC_CASTLE_CONFIGURATION,
    )
    assert res.get_json() == {"message": "The cluster does not exist"}
    assert res.status_code != 200
