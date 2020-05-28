from server import app
from os import path
from shutil import rmtree, copytree
from models.cluster_status_code import ClusterStatusCode
from pathlib import Path
import pytest

NON_EXISTING_CLUSTER_NAME = "non-existing"
EXISTING_CLUSTER_NAME = "valid-1"

NON_EXISTING_CLUSTER_CONFIGURATION = {
    "cluster_name": "non-existing",
    "domain": "example.com",
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
EXISTING_CLUSTER_CONFIGURATION = {
    "cluster_name": "valid-1",
    "domain": "example.com",
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
EXISTING_CLUSTER_STATE = {
    "cluster_name": "valid-1",
    "nb_users": 10,
    "guest_passwd": "password-123",
    "storage": {
        "type": "nfs",
        "home_size": 100,
        "scratch_size": 50,
        "project_size": 50,
    },
    "instances": {
        "mgmt": {"type": "p4-6gb", "count": 1},
        "login": {"type": "p4-6gb", "count": 1},
        "node": {"type": "p2-3gb", "count": 1},
    },
    "domain": "example.com",
    "public_keys": ["ssh-rsa FAKE"],
    "image": "CentOS-7-x64-2019-07",
    "os_floating_ips": ["100.101.102.103"],
}


@pytest.fixture
def client(mocker):
    app.config["TESTING"] = True
    copytree(
        path.join(Path(__file__).parent.parent, "mock-clusters", "valid-1"),
        "/home/mcu/clusters/valid-1",
    )
    mocker.patch(
        "models.openstack_manager.OpenStackManager.__init__", return_value=None
    )
    mocker.patch(
        "models.openstack_manager.OpenStackManager.get_available_floating_ips",
        return_value=["1.2.3.4"],
    )

    with app.test_client() as client:
        yield client

    rmtree("/home/mcu/clusters/valid-1")


# GET /api/magic-castle/<cluster_name>
def test_get_state_existing(client):
    res = client.get(f"/api/magic-castle/{EXISTING_CLUSTER_NAME}")
    assert res.get_json() == EXISTING_CLUSTER_STATE
    assert res.status_code == 200


def test_get_state_non_existing(client):
    res = client.get(f"/api/magic-castle/{NON_EXISTING_CLUSTER_NAME}")
    assert res.get_json() == {"message": "This cluster does not exist"}
    assert res.status_code != 200


# GET /api/magic-castle/<cluster_name>/status
def test_get_status(client):
    res = client.get(f"/api/magic-castle/{NON_EXISTING_CLUSTER_NAME}/status")
    assert res.get_json() == {"status": "not_found"}

    modify_cluster_status(EXISTING_CLUSTER_NAME, ClusterStatusCode.BUILD_RUNNING)
    res = client.get(f"/api/magic-castle/{EXISTING_CLUSTER_NAME}/status")
    assert res.get_json() == {"status": "build_running"}

    modify_cluster_status(EXISTING_CLUSTER_NAME, ClusterStatusCode.BUILD_SUCCESS)
    res = client.get(f"/api/magic-castle/{EXISTING_CLUSTER_NAME}/status")
    assert res.get_json() == {"status": "build_success"}

    modify_cluster_status(EXISTING_CLUSTER_NAME, ClusterStatusCode.BUILD_ERROR)
    res = client.get(f"/api/magic-castle/{EXISTING_CLUSTER_NAME}/status")
    assert res.get_json() == {"status": "build_error"}

    modify_cluster_status(EXISTING_CLUSTER_NAME, ClusterStatusCode.DESTROY_RUNNING)
    res = client.get(f"/api/magic-castle/{EXISTING_CLUSTER_NAME}/status")
    assert res.get_json() == {"status": "destroy_running"}

    modify_cluster_status(EXISTING_CLUSTER_NAME, ClusterStatusCode.DESTROY_ERROR)
    res = client.get(f"/api/magic-castle/{EXISTING_CLUSTER_NAME}/status")
    assert res.get_json() == {"status": "destroy_error"}

    modify_cluster_status(EXISTING_CLUSTER_NAME, ClusterStatusCode.IDLE)
    res = client.get(f"/api/magic-castle/{EXISTING_CLUSTER_NAME}/status")
    assert res.get_json() == {"status": "idle"}


# DELETE /api/magic-castle/<cluster_name>
def test_delete_invalid_status(client):
    res = client.delete(f"/api/magic-castle/{NON_EXISTING_CLUSTER_NAME}")
    assert res.get_json() == {"message": "This cluster does not exist"}
    assert res.status_code != 200

    modify_cluster_status(EXISTING_CLUSTER_NAME, ClusterStatusCode.DESTROY_RUNNING)
    res = client.delete(f"/api/magic-castle/{EXISTING_CLUSTER_NAME}")
    assert res.get_json() == {"message": "This cluster is busy"}
    assert res.status_code != 200

    modify_cluster_status(EXISTING_CLUSTER_NAME, ClusterStatusCode.BUILD_RUNNING)
    res = client.delete(f"/api/magic-castle/{EXISTING_CLUSTER_NAME}")
    assert res.get_json() == {"message": "This cluster is busy"}
    assert res.status_code != 200


# PUT /api/magic-castle/<cluster_name>
def test_modify_invalid_status(client):
    res = client.put(
        f"/api/magic-castle/{NON_EXISTING_CLUSTER_NAME}",
        json=NON_EXISTING_CLUSTER_CONFIGURATION,
    )
    assert res.get_json() == {"message": "This cluster does not exist"}
    assert res.status_code != 200

    modify_cluster_status(EXISTING_CLUSTER_NAME, ClusterStatusCode.BUILD_RUNNING)
    res = client.put(
        f"/api/magic-castle/{EXISTING_CLUSTER_NAME}",
        json=EXISTING_CLUSTER_CONFIGURATION,
    )
    assert res.get_json() == {"message": "This cluster is busy"}
    assert res.status_code != 200

    modify_cluster_status(EXISTING_CLUSTER_NAME, ClusterStatusCode.DESTROY_RUNNING)
    res = client.put(
        f"/api/magic-castle/{EXISTING_CLUSTER_NAME}",
        json=EXISTING_CLUSTER_CONFIGURATION,
    )
    assert res.get_json() == {"message": "This cluster is busy"}
    assert res.status_code != 200


def modify_cluster_status(cluster_name, status: ClusterStatusCode):
    with open(f"/home/mcu/clusters/{cluster_name}/status.txt", "w") as status_file:
        status_file.write(status.value)
