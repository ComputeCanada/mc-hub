import pytest
from server import app
from time import time, sleep
from os import path
from random import randrange

"""
This implementation test suite does not use any mocking. Instead, it creates, modifies and destroys a live cluster
using the OpenStack clouds.yaml, configuration.json and gcloud-key.json provided to the container.

The auth_type variable in configuration.json must be set to "SAML" for these tests to work properly.

These tests are marked as slow. To run these tests, the cli argument --build-live-cluster needs to be added.

They also need to be run in the right order, otherwise they will fail.

If some tests fail, you may need to manually destroy the cluster created in OpenStack.

References:
https://docs.pytest.org/en/latest/example/simple.html#control-skipping-of-tests-according-to-command-line-option
"""

# Using a dynamic cluster name to avoid bans from Let's Encrypt when making too many certificate requests
CLUSTER_NAME = "trulygreatcluster" + str(randrange(100000))

HOSTNAME = f"{CLUSTER_NAME}.calculquebec.cloud"
JOHN_DOE_HEADERS = {
    "eduPersonPrincipalName": "john.doe@computecanada.ca",
    "givenName": "John",
    "surname": "Doe",
    "mail": "john.doe@example.com",
}


@pytest.fixture
def client(mocker):
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture(autouse=True)
def disable_provisionning_polling(mocker):
    """
    ProvisioningManager continues polling the cluster status at the end of the tests.
    To avoid this behaviour, we mock ProvisioningManager.is_busy.
    """
    mocker.patch(
        "models.puppet.provisioning_manager.ProvisioningManager.is_busy",
        return_value=True,
    )


@pytest.mark.build_live_cluster
def test_plan_creation(client):
    res = client.post(
        f"/api/magic-castles",
        json={
            "cluster_name": CLUSTER_NAME,
            "nb_users": 10,
            "guest_passwd": "",
            "storage": {
                "type": "nfs",
                "home_size": 50,
                "scratch_size": 5,
                "project_size": 5,
            },
            "instances": {
                "mgmt": {"type": "p4-6gb", "count": 1},
                "login": {"type": "p4-6gb", "count": 1},
                "node": {"type": "p2-3gb", "count": 1},
            },
            "domain": "calculquebec.cloud",
            "public_keys": [
                "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQDB2S4ftDLiz1IrD2Lj+4QmtWgGnTAwsTQfx4GwNcC3mOfZkL/raNIUBZn7xjOjDzkOQ9k37T/aaQNnz/yBhdeydKJHKuS+J2gscMAAc+2zXNyAEfWlrv0aPX0EGhkYwsjsumQ4k9wO6+GNlA+Z3sisNB8Jo/JtxIQ6B2t16Ru2Qe07G+NTZWMLuB++8j+eJW2Ux8B7n14Vf+lPwzz4TbjjIbueugh9JRcdfXa/FclEvnZwgO61tbHjJJNH+FCHyxWraTEB1//COaAGfwekK17T/83Wi3Avdr5ZL+ffgVbVwVZXCuq3PTc3qmthRxxe/DBjcJYsGuRa0/f7U5bCKYYflL+U2nDmlfBbCYFvFFje9K3NXjmZJZWf1L31fVWE1doj9BgRwXMFC/WMx7jt3TUcdGXsWICHU7jMtywUSf/i10dzs+BgpAnH7XeCswHekfaNseKdFDWY6c7egsfbT16BzQn+hBlrEQ3UNlFf/ye9aVSdTppjIKD3IqV8qrDqB2s= noname"
            ],
            "image": "CentOS-7-x64-2020-03",
            "os_floating_ips": ["Automatic allocation"],
        },
        headers=JOHN_DOE_HEADERS,
    )
    assert res.get_json() == {}
    assert res.status_code == 200


@pytest.mark.build_live_cluster
def test_apply_creation_plan(client):
    res = client.post(f"/api/magic-castles/{HOSTNAME}/apply", headers=JOHN_DOE_HEADERS)
    assert res.get_json() == {}
    assert res.status_code == 200


@pytest.mark.build_live_cluster
def test_creation_running(client):
    res = client.get(f"/api/magic-castles/{HOSTNAME}/status", headers=JOHN_DOE_HEADERS)
    assert res.get_json()["status"] == "build_running"
    assert res.status_code == 200


@pytest.mark.build_live_cluster
def test_create_success(client):
    max_timeout_seconds = 480  # 8 minutes.
    start_time = time()
    status = client.get(
        f"/api/magic-castles/{HOSTNAME}/status", headers=JOHN_DOE_HEADERS
    ).get_json()["status"]
    while status == "build_running" and time() - start_time <= max_timeout_seconds:
        status = client.get(
            f"/api/magic-castles/{HOSTNAME}/status", headers=JOHN_DOE_HEADERS
        ).get_json()["status"]
    assert status == "provisioning_running"
    state = client.get(
        f"/api/magic-castles/{HOSTNAME}", headers=JOHN_DOE_HEADERS
    ).get_json()

    # os_floating_ips key is omitted, as we don't know the value yet
    assert {
        "cluster_name": CLUSTER_NAME,
        "nb_users": 10,
        "storage": {
            "type": "nfs",
            "home_size": 50,
            "scratch_size": 5,
            "project_size": 5,
        },
        "instances": {
            "mgmt": {"type": "p4-6gb", "count": 1},
            "login": {"type": "p4-6gb", "count": 1},
            "node": {"type": "p2-3gb", "count": 1},
        },
        "domain": "calculquebec.cloud",
        "public_keys": [
            "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQDB2S4ftDLiz1IrD2Lj+4QmtWgGnTAwsTQfx4GwNcC3mOfZkL/raNIUBZn7xjOjDzkOQ9k37T/aaQNnz/yBhdeydKJHKuS+J2gscMAAc+2zXNyAEfWlrv0aPX0EGhkYwsjsumQ4k9wO6+GNlA+Z3sisNB8Jo/JtxIQ6B2t16Ru2Qe07G+NTZWMLuB++8j+eJW2Ux8B7n14Vf+lPwzz4TbjjIbueugh9JRcdfXa/FclEvnZwgO61tbHjJJNH+FCHyxWraTEB1//COaAGfwekK17T/83Wi3Avdr5ZL+ffgVbVwVZXCuq3PTc3qmthRxxe/DBjcJYsGuRa0/f7U5bCKYYflL+U2nDmlfBbCYFvFFje9K3NXjmZJZWf1L31fVWE1doj9BgRwXMFC/WMx7jt3TUcdGXsWICHU7jMtywUSf/i10dzs+BgpAnH7XeCswHekfaNseKdFDWY6c7egsfbT16BzQn+hBlrEQ3UNlFf/ye9aVSdTppjIKD3IqV8qrDqB2s= noname"
        ],
        "image": "CentOS-7-x64-2020-03",
    }.items() < state.items()


@pytest.mark.build_live_cluster
def test_plan_modify(client):
    """
    Modifying the node instance type and count.
    """
    res = client.put(
        f"/api/magic-castles/{HOSTNAME}",
        json={
            "cluster_name": CLUSTER_NAME,
            "nb_users": 10,
            "guest_passwd": "",
            "storage": {
                "type": "nfs",
                "home_size": 50,
                "scratch_size": 5,
                "project_size": 5,
            },
            "instances": {
                "mgmt": {"type": "p4-6gb", "count": 1},
                "login": {"type": "p4-6gb", "count": 1},
                "node": {"type": "c2-7.5gb-31", "count": 3},
            },
            "domain": "calculquebec.cloud",
            "public_keys": [
                "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQDB2S4ftDLiz1IrD2Lj+4QmtWgGnTAwsTQfx4GwNcC3mOfZkL/raNIUBZn7xjOjDzkOQ9k37T/aaQNnz/yBhdeydKJHKuS+J2gscMAAc+2zXNyAEfWlrv0aPX0EGhkYwsjsumQ4k9wO6+GNlA+Z3sisNB8Jo/JtxIQ6B2t16Ru2Qe07G+NTZWMLuB++8j+eJW2Ux8B7n14Vf+lPwzz4TbjjIbueugh9JRcdfXa/FclEvnZwgO61tbHjJJNH+FCHyxWraTEB1//COaAGfwekK17T/83Wi3Avdr5ZL+ffgVbVwVZXCuq3PTc3qmthRxxe/DBjcJYsGuRa0/f7U5bCKYYflL+U2nDmlfBbCYFvFFje9K3NXjmZJZWf1L31fVWE1doj9BgRwXMFC/WMx7jt3TUcdGXsWICHU7jMtywUSf/i10dzs+BgpAnH7XeCswHekfaNseKdFDWY6c7egsfbT16BzQn+hBlrEQ3UNlFf/ye9aVSdTppjIKD3IqV8qrDqB2s= noname"
            ],
            "image": "CentOS-7-x64-2020-03",
            "os_floating_ips": [],
        },
        headers=JOHN_DOE_HEADERS,
    )
    assert res.get_json() == {}
    assert res.status_code == 200


@pytest.mark.build_live_cluster
def test_apply_modification_plan(client):
    res = client.post(f"/api/magic-castles/{HOSTNAME}/apply", headers=JOHN_DOE_HEADERS)
    assert res.get_json() == {}
    assert res.status_code == 200


@pytest.mark.build_live_cluster
def test_modify_success(client):
    max_timeout_seconds = 360  # 6 minutes.
    start_time = time()
    status = client.get(
        f"/api/magic-castles/{HOSTNAME}/status", headers=JOHN_DOE_HEADERS
    ).get_json()["status"]
    while status == "build_running" and time() - start_time <= max_timeout_seconds:
        status = client.get(
            f"/api/magic-castles/{HOSTNAME}/status", headers=JOHN_DOE_HEADERS
        ).get_json()["status"]
    assert status == "provisioning_running"
    state = client.get(
        f"/api/magic-castles/{HOSTNAME}", headers=JOHN_DOE_HEADERS
    ).get_json()

    # os_floating_ips key is omitted, as we don't know the value yet
    assert {
        "cluster_name": CLUSTER_NAME,
        "nb_users": 10,
        "storage": {
            "type": "nfs",
            "home_size": 50,
            "scratch_size": 5,
            "project_size": 5,
        },
        "instances": {
            "mgmt": {"type": "p4-6gb", "count": 1},
            "login": {"type": "p4-6gb", "count": 1},
            "node": {"type": "c2-7.5gb-31", "count": 3},
        },
        "domain": "calculquebec.cloud",
        "public_keys": [
            "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQDB2S4ftDLiz1IrD2Lj+4QmtWgGnTAwsTQfx4GwNcC3mOfZkL/raNIUBZn7xjOjDzkOQ9k37T/aaQNnz/yBhdeydKJHKuS+J2gscMAAc+2zXNyAEfWlrv0aPX0EGhkYwsjsumQ4k9wO6+GNlA+Z3sisNB8Jo/JtxIQ6B2t16Ru2Qe07G+NTZWMLuB++8j+eJW2Ux8B7n14Vf+lPwzz4TbjjIbueugh9JRcdfXa/FclEvnZwgO61tbHjJJNH+FCHyxWraTEB1//COaAGfwekK17T/83Wi3Avdr5ZL+ffgVbVwVZXCuq3PTc3qmthRxxe/DBjcJYsGuRa0/f7U5bCKYYflL+U2nDmlfBbCYFvFFje9K3NXjmZJZWf1L31fVWE1doj9BgRwXMFC/WMx7jt3TUcdGXsWICHU7jMtywUSf/i10dzs+BgpAnH7XeCswHekfaNseKdFDWY6c7egsfbT16BzQn+hBlrEQ3UNlFf/ye9aVSdTppjIKD3IqV8qrDqB2s= noname"
        ],
        "image": "CentOS-7-x64-2020-03",
    }.items() < state.items()


@pytest.mark.build_live_cluster
def test_plan_destroy(client):
    res = client.delete(f"/api/magic-castles/{HOSTNAME}", headers=JOHN_DOE_HEADERS)
    assert res.get_json() == {}
    assert res.status_code == 200


@pytest.mark.build_live_cluster
def test_apply_destruction_plan(client):
    res = client.post(f"/api/magic-castles/{HOSTNAME}/apply", headers=JOHN_DOE_HEADERS)
    assert res.get_json() == {}
    assert res.status_code == 200


@pytest.mark.build_live_cluster
def test_destroy_success(client):
    max_timeout_seconds = 180  # 3 minutes.
    start_time = time()
    status = client.get(
        f"/api/magic-castles/{HOSTNAME}/status", headers=JOHN_DOE_HEADERS
    ).get_json()["status"]
    while status == "destroy_running" and time() - start_time <= max_timeout_seconds:
        status = client.get(
            f"/api/magic-castles/{HOSTNAME}/status", headers=JOHN_DOE_HEADERS
        ).get_json()["status"]
    assert status == "not_found"


@pytest.mark.build_live_cluster
def test_cluster_folder_deleted():
    sleep(1)  # Status is "not_found" before the cluster folder is deleted
    assert not path.exists(f"/home/mcu/clusters/{HOSTNAME}")
