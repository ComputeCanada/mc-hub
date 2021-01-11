from server import app
from models.magic_castle.cluster_status_code import ClusterStatusCode
from tests.test_helpers import *
from os import path
import sqlite3
import pytest
from tests.mocks.configuration.config_mock import config_auth_saml_mock


NON_EXISTING_HOSTNAME = "nonexisting.calculquebec.cloud"
EXISTING_HOSTNAME = "valid1.calculquebec.cloud"

NON_EXISTING_CLUSTER_CONFIGURATION = {
    "cluster_name": "nonexisting",
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
EXISTING_CLUSTER_CONFIGURATION = {
    "cluster_name": "valid1",
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
EXISTING_CLUSTER_STATE = {
    "cluster_name": "valid1",
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
    "domain": "calculquebec.cloud",
    "public_keys": ["ssh-rsa FAKE"],
    "image": "CentOS-7-x64-2019-07",
    "os_floating_ips": ["100.101.102.103"],
}

ALICE_HEADERS = {
    "eduPersonPrincipalName": "alice@computecanada.ca",
    "givenName": "Alice",
    "surname": "Tremblay",
    "mail": "alice.tremblay@example.com",
}

BOB_HEADERS = {
    "eduPersonPrincipalName": "bob12.bobby@computecanada.ca",
    "givenName": "Bob",
    "surname": "Rodriguez",
    "mail": "bob-rodriguez435@example.com",
}


@pytest.fixture
def client(mocker):
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


# GET /api/users/me
def test_get_current_user_authentified(client):
    res = client.get(f"/api/users/me", headers=ALICE_HEADERS)
    assert res.get_json() == {"full_name": "Alice Tremblay", "username": "alice"}
    res = client.get(f"/api/users/me", headers=BOB_HEADERS)
    assert res.get_json() == {
        "full_name": "Bob Rodriguez",
        "username": "bob12.bobby",
    }


# GET /api/users/me
def test_get_current_user_non_authentified(client):
    res = client.get(f"/api/users/me")
    assert res.get_json() == {"message": "You need to be authenticated"}


# GET /api/magic_castle
def test_get_all_magic_castle_names(client):
    res = client.get(f"/api/magic-castles", headers=ALICE_HEADERS)
    assert res.get_json() == [
        {
            "cluster_name": "buildplanning",
            "domain": "calculquebec.cloud",
            "image": "CentOS-7-x64-2019-07",
            "nb_users": 34,
            "instances": {
                "mgmt": {"type": "c2-7.5gb-31", "count": 1},
                "login": {"type": "p4-6gb", "count": 1},
                "node": {"type": "c1-7.5gb-30", "count": 5},
            },
            "storage": {
                "type": "nfs",
                "home_size": 73,
                "project_size": 1,
                "scratch_size": 1,
            },
            "public_keys": ["ssh-rsa FAKE"],
            "guest_passwd": "",
            "os_floating_ips": ["Automatic allocation"],
            "hostname": "buildplanning.calculquebec.cloud",
            "status": "plan_running",
            "freeipa_passwd": None,
            "owner": "alice",
        },
        {
            "cluster_name": "created",
            "domain": "calculquebec.cloud",
            "image": "CentOS-7-x64-2019-07",
            "nb_users": 34,
            "instances": {
                "mgmt": {"type": "c2-7.5gb-31", "count": 1},
                "login": {"type": "p4-6gb", "count": 1},
                "node": {"type": "c1-7.5gb-30", "count": 5},
            },
            "storage": {
                "type": "nfs",
                "home_size": 73,
                "project_size": 1,
                "scratch_size": 1,
            },
            "public_keys": ["ssh-rsa FAKE"],
            "guest_passwd": "",
            "os_floating_ips": ["Automatic allocation"],
            "hostname": "created.calculquebec.cloud",
            "status": "created",
            "freeipa_passwd": None,
            "owner": "alice",
        },
        {
            "cluster_name": "valid1",
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
            "os_floating_ips": ["Automatic allocation"],
            "hostname": "valid1.calculquebec.cloud",
            "status": "provisioning_success",
            "freeipa_passwd": "FAKE",
            "owner": "alice",
        },
    ]
    assert res.status_code == 200


def test_get_all_magic_castles_unauthenticated(client):
    # No authentication header at all
    res = client.get(f"/api/magic-castles")
    assert res.get_json() == {"message": "You need to be authenticated"}
    assert res.status_code != 200

    # Missing some authentication headers
    res = client.get(
        f"/api/magic-castles",
        headers={"eduPersonPrincipalName": "alice@computecanada.ca"},
    )
    assert res.get_json() == {"message": "You need to be authenticated"}
    assert res.status_code != 200


# GET /api/magic-castles/<hostname>
def test_get_state_existing(client):
    res = client.get(f"/api/magic-castles/{EXISTING_HOSTNAME}", headers=ALICE_HEADERS)
    assert res.get_json() == EXISTING_CLUSTER_STATE
    assert res.status_code == 200


def test_get_state_non_existing(client):
    res = client.get(
        f"/api/magic-castles/{NON_EXISTING_HOSTNAME}", headers=ALICE_HEADERS
    )
    assert res.get_json() == {"message": "This cluster does not exist"}
    assert res.status_code != 200


def test_get_state_not_owned(client):
    res = client.get(
        f"/api/magic-castles/missingfloatingips.c3.ca", headers=ALICE_HEADERS
    )
    assert res.get_json() == {"message": "This cluster does not exist"}
    assert res.status_code != 200


# GET /api/magic-castles/<hostname>/status
def test_get_status(mocker, client):
    res = client.get(
        f"/api/magic-castles/missingfloatingips.c3.ca/status", headers=BOB_HEADERS
    )
    assert res.get_json() == {
        "status": "build_running",
        "progress": [
            {
                "address": "module.openstack.data.template_cloudinit_config.login_config[0]",
                "type": "template_cloudinit_config",
                "change": {"actions": ["read"], "progress": "done"},
            },
            {
                "address": "module.openstack.data.template_cloudinit_config.mgmt_config[0]",
                "type": "template_cloudinit_config",
                "change": {"actions": ["read"], "progress": "done"},
            },
            {
                "address": 'module.openstack.data.template_cloudinit_config.node_config["node1"]',
                "type": "template_cloudinit_config",
                "change": {"actions": ["read"], "progress": "done"},
            },
            {
                "address": 'module.openstack.data.template_cloudinit_config.node_config["node2"]',
                "type": "template_cloudinit_config",
                "change": {"actions": ["read"], "progress": "done"},
            },
            {
                "address": 'module.openstack.data.template_cloudinit_config.node_config["node3"]',
                "type": "template_cloudinit_config",
                "change": {"actions": ["read"], "progress": "done"},
            },
            {
                "address": "module.openstack.data.template_file.hieradata",
                "type": "template_file",
                "change": {"actions": ["read"], "progress": "done"},
            },
            {
                "address": "module.openstack.openstack_blockstorage_volume_v2.home[0]",
                "type": "openstack_blockstorage_volume_v2",
                "change": {"actions": ["create"], "progress": "done"},
            },
            {
                "address": "module.openstack.openstack_blockstorage_volume_v2.project[0]",
                "type": "openstack_blockstorage_volume_v2",
                "change": {"actions": ["create"], "progress": "done"},
            },
            {
                "address": "module.openstack.openstack_blockstorage_volume_v2.scratch[0]",
                "type": "openstack_blockstorage_volume_v2",
                "change": {"actions": ["create"], "progress": "done"},
            },
            {
                "address": "module.openstack.openstack_compute_floatingip_associate_v2.fip[0]",
                "type": "openstack_compute_floatingip_associate_v2",
                "change": {"actions": ["create"], "progress": "queued"},
            },
            {
                "address": "module.openstack.openstack_compute_instance_v2.login[0]",
                "type": "openstack_compute_instance_v2",
                "change": {"actions": ["create"], "progress": "done"},
            },
            {
                "address": "module.openstack.openstack_compute_instance_v2.mgmt[0]",
                "type": "openstack_compute_instance_v2",
                "change": {"actions": ["create"], "progress": "done"},
            },
            {
                "address": 'module.openstack.openstack_compute_instance_v2.node["node1"]',
                "type": "openstack_compute_instance_v2",
                "change": {"actions": ["create"], "progress": "done"},
            },
            {
                "address": 'module.openstack.openstack_compute_instance_v2.node["node2"]',
                "type": "openstack_compute_instance_v2",
                "change": {"actions": ["create"], "progress": "done"},
            },
            {
                "address": 'module.openstack.openstack_compute_instance_v2.node["node3"]',
                "type": "openstack_compute_instance_v2",
                "change": {"actions": ["create"], "progress": "done"},
            },
            {
                "address": "module.openstack.openstack_compute_keypair_v2.keypair",
                "type": "openstack_compute_keypair_v2",
                "change": {"actions": ["create"], "progress": "done"},
            },
            {
                "address": "module.openstack.openstack_compute_secgroup_v2.secgroup_1",
                "type": "openstack_compute_secgroup_v2",
                "change": {"actions": ["create"], "progress": "done"},
            },
            {
                "address": "module.openstack.openstack_compute_volume_attach_v2.va_home[0]",
                "type": "openstack_compute_volume_attach_v2",
                "change": {"actions": ["create"], "progress": "done"},
            },
            {
                "address": "module.openstack.openstack_compute_volume_attach_v2.va_project[0]",
                "type": "openstack_compute_volume_attach_v2",
                "change": {"actions": ["create"], "progress": "done"},
            },
            {
                "address": "module.openstack.openstack_compute_volume_attach_v2.va_scratch[0]",
                "type": "openstack_compute_volume_attach_v2",
                "change": {"actions": ["create"], "progress": "done"},
            },
            {
                "address": "module.openstack.openstack_networking_floatingip_v2.fip[0]",
                "type": "openstack_networking_floatingip_v2",
                "change": {"actions": ["create"], "progress": "running"},
            },
            {
                "address": "module.openstack.openstack_networking_port_v2.port_login[0]",
                "type": "openstack_networking_port_v2",
                "change": {"actions": ["create"], "progress": "done"},
            },
            {
                "address": "module.openstack.openstack_networking_port_v2.port_mgmt[0]",
                "type": "openstack_networking_port_v2",
                "change": {"actions": ["create"], "progress": "done"},
            },
            {
                "address": 'module.openstack.openstack_networking_port_v2.port_node["node1"]',
                "type": "openstack_networking_port_v2",
                "change": {"actions": ["create"], "progress": "done"},
            },
            {
                "address": 'module.openstack.openstack_networking_port_v2.port_node["node2"]',
                "type": "openstack_networking_port_v2",
                "change": {"actions": ["create"], "progress": "done"},
            },
            {
                "address": 'module.openstack.openstack_networking_port_v2.port_node["node3"]',
                "type": "openstack_networking_port_v2",
                "change": {"actions": ["create"], "progress": "done"},
            },
            {
                "address": "module.openstack.random_pet.guest_passwd[0]",
                "type": "random_pet",
                "change": {"actions": ["create"], "progress": "done"},
            },
            {
                "address": "module.openstack.random_string.freeipa_passwd",
                "type": "random_string",
                "change": {"actions": ["create"], "progress": "done"},
            },
            {
                "address": "module.openstack.random_string.munge_key",
                "type": "random_string",
                "change": {"actions": ["create"], "progress": "done"},
            },
            {
                "address": "module.openstack.random_string.puppetmaster_password",
                "type": "random_string",
                "change": {"actions": ["create"], "progress": "done"},
            },
            {
                "address": "module.openstack.random_uuid.consul_token",
                "type": "random_uuid",
                "change": {"actions": ["create"], "progress": "done"},
            },
            {
                "address": "module.openstack.tls_private_key.login_rsa",
                "type": "tls_private_key",
                "change": {"actions": ["create"], "progress": "done"},
            },
        ],
    }


def test_get_status_code(client, database_connection):
    res = client.get(
        f"/api/magic-castles/{NON_EXISTING_HOSTNAME}/status", headers=ALICE_HEADERS
    )
    assert res.get_json()["status"] == "not_found"

    modify_cluster_status(
        database_connection, EXISTING_HOSTNAME, ClusterStatusCode.BUILD_RUNNING
    )
    res = client.get(
        f"/api/magic-castles/{EXISTING_HOSTNAME}/status", headers=ALICE_HEADERS
    )
    assert res.get_json()["status"] == "build_running"

    modify_cluster_status(
        database_connection, EXISTING_HOSTNAME, ClusterStatusCode.PROVISIONING_SUCCESS
    )
    res = client.get(
        f"/api/magic-castles/{EXISTING_HOSTNAME}/status", headers=ALICE_HEADERS
    )
    assert res.get_json()["status"] == "provisioning_success"

    modify_cluster_status(
        database_connection, EXISTING_HOSTNAME, ClusterStatusCode.BUILD_ERROR
    )
    res = client.get(
        f"/api/magic-castles/{EXISTING_HOSTNAME}/status", headers=ALICE_HEADERS
    )
    assert res.get_json()["status"] == "build_error"

    modify_cluster_status(
        database_connection, EXISTING_HOSTNAME, ClusterStatusCode.DESTROY_RUNNING
    )
    res = client.get(
        f"/api/magic-castles/{EXISTING_HOSTNAME}/status", headers=ALICE_HEADERS
    )
    assert res.get_json()["status"] == "destroy_running"

    modify_cluster_status(
        database_connection, EXISTING_HOSTNAME, ClusterStatusCode.DESTROY_ERROR
    )
    res = client.get(
        f"/api/magic-castles/{EXISTING_HOSTNAME}/status", headers=ALICE_HEADERS
    )
    assert res.get_json()["status"] == "destroy_error"


# DELETE /api/magic-castles/<hostname>
def test_delete_invalid_status(database_connection, client):
    res = client.delete(
        f"/api/magic-castles/{NON_EXISTING_HOSTNAME}", headers=ALICE_HEADERS
    )
    assert res.get_json() == {"message": "This cluster does not exist"}
    assert res.status_code != 200

    modify_cluster_status(
        database_connection, EXISTING_HOSTNAME, ClusterStatusCode.DESTROY_RUNNING
    )
    res = client.delete(
        f"/api/magic-castles/{EXISTING_HOSTNAME}", headers=ALICE_HEADERS
    )
    assert res.get_json() == {"message": "This cluster is busy"}
    assert res.status_code != 200

    modify_cluster_status(
        database_connection, EXISTING_HOSTNAME, ClusterStatusCode.BUILD_RUNNING
    )
    res = client.delete(
        f"/api/magic-castles/{EXISTING_HOSTNAME}", headers=ALICE_HEADERS
    )
    assert res.get_json() == {"message": "This cluster is busy"}
    assert res.status_code != 200


# PUT /api/magic-castles/<hostname>
def test_modify_invalid_status(database_connection, client):
    res = client.put(
        f"/api/magic-castles/{NON_EXISTING_HOSTNAME}",
        json=NON_EXISTING_CLUSTER_CONFIGURATION,
        headers=ALICE_HEADERS,
    )
    assert res.get_json() == {"message": "This cluster does not exist"}
    assert res.status_code != 200

    modify_cluster_status(
        database_connection, EXISTING_HOSTNAME, ClusterStatusCode.BUILD_RUNNING
    )
    res = client.put(
        f"/api/magic-castles/{EXISTING_HOSTNAME}",
        json=EXISTING_CLUSTER_CONFIGURATION,
        headers=ALICE_HEADERS,
    )
    assert res.get_json() == {"message": "This cluster is busy"}
    assert res.status_code != 200

    modify_cluster_status(
        database_connection, EXISTING_HOSTNAME, ClusterStatusCode.DESTROY_RUNNING
    )
    res = client.put(
        f"/api/magic-castles/{EXISTING_HOSTNAME}",
        json=EXISTING_CLUSTER_CONFIGURATION,
        headers=ALICE_HEADERS,
    )
    assert res.get_json() == {"message": "This cluster is busy"}
    assert res.status_code != 200


def modify_cluster_status(database_connection, hostname, status: ClusterStatusCode):
    database_connection.execute(
        "UPDATE magic_castles SET status = ? WHERE hostname = ?",
        (status.value, hostname),
    )
    database_connection.commit()
