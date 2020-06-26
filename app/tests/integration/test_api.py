from server import app
from models.cluster_status_code import ClusterStatusCode
from tests.test_helpers import *
from os import path

NON_EXISTING_HOSTNAME = "nonexisting"
EXISTING_HOSTNAME = "valid1.calculquebec.cloud"

NON_EXISTING_CLUSTER_CONFIGURATION = {
    "cluster_name": "nonexisting",
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


@pytest.fixture
def client(mocker):
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


# GET /api/magic_castle
def test_get_all_magic_castle_names(client):
    res = client.get(f"/api/magic-castle")
    assert res.get_json() == [
        {
            "cluster_name": "empty",
            "domain": "calculquebec.cloud",
            "hostname": "empty.calculquebec.cloud",
            "status": "build_error",
        },
        {
            "cluster_name": "missingfloatingips",
            "domain": "c3.ca",
            "hostname": "missingfloatingips.c3.ca",
            "status": "build_running",
        },
        {
            "cluster_name": "missingnodes",
            "domain": "sub.example.com",
            "hostname": "missingnodes.sub.example.com",
            "status": "build_error",
        },
        {
            "cluster_name": "valid1",
            "domain": "calculquebec.cloud",
            "hostname": "valid1.calculquebec.cloud",
            "status": "build_success",
        },
    ]
    assert res.status_code == 200


# GET /api/magic-castle/<hostname>
def test_get_state_existing(client):
    res = client.get(f"/api/magic-castle/{EXISTING_HOSTNAME}")
    assert res.get_json() == EXISTING_CLUSTER_STATE
    assert res.status_code == 200


def test_get_state_non_existing(client):
    res = client.get(f"/api/magic-castle/{NON_EXISTING_HOSTNAME}")
    assert res.get_json() == {"message": "This cluster does not exist"}
    assert res.status_code != 200


# GET /api/magic-castle/<hostname>/status
def test_get_status(mocker, client):
    mocker.patch("models.magic_castle.MagicCastle._MagicCastle__generate_plan_file")
    res = client.get(f"/api/magic-castle/missingfloatingips.c3.ca/status")
    assert res.get_json() == {
        "status": "build_running",
        "progress": [
            {
                "address": "module.openstack.data.template_cloudinit_config.login_config[0]",
                "type": "template_cloudinit_config",
                "change": {"actions": ["read"], "done": True},
            },
            {
                "address": "module.openstack.data.template_cloudinit_config.mgmt_config[0]",
                "type": "template_cloudinit_config",
                "change": {"actions": ["read"], "done": True},
            },
            {
                "address": 'module.openstack.data.template_cloudinit_config.node_config["node1"]',
                "type": "template_cloudinit_config",
                "change": {"actions": ["read"], "done": True},
            },
            {
                "address": 'module.openstack.data.template_cloudinit_config.node_config["node2"]',
                "type": "template_cloudinit_config",
                "change": {"actions": ["read"], "done": True},
            },
            {
                "address": 'module.openstack.data.template_cloudinit_config.node_config["node3"]',
                "type": "template_cloudinit_config",
                "change": {"actions": ["read"], "done": True},
            },
            {
                "address": "module.openstack.data.template_file.hieradata",
                "type": "template_file",
                "change": {"actions": ["read"], "done": True},
            },
            {
                "address": "module.openstack.openstack_blockstorage_volume_v2.home[0]",
                "type": "openstack_blockstorage_volume_v2",
                "change": {"actions": ["create"], "done": True},
            },
            {
                "address": "module.openstack.openstack_blockstorage_volume_v2.project[0]",
                "type": "openstack_blockstorage_volume_v2",
                "change": {"actions": ["create"], "done": True},
            },
            {
                "address": "module.openstack.openstack_blockstorage_volume_v2.scratch[0]",
                "type": "openstack_blockstorage_volume_v2",
                "change": {"actions": ["create"], "done": True},
            },
            {
                "address": "module.openstack.openstack_compute_floatingip_associate_v2.fip[0]",
                "type": "openstack_compute_floatingip_associate_v2",
                "change": {"actions": ["create"], "done": False},
            },
            {
                "address": "module.openstack.openstack_compute_instance_v2.login[0]",
                "type": "openstack_compute_instance_v2",
                "change": {"actions": ["create"], "done": True},
            },
            {
                "address": "module.openstack.openstack_compute_instance_v2.mgmt[0]",
                "type": "openstack_compute_instance_v2",
                "change": {"actions": ["create"], "done": True},
            },
            {
                "address": 'module.openstack.openstack_compute_instance_v2.node["node1"]',
                "type": "openstack_compute_instance_v2",
                "change": {"actions": ["create"], "done": True},
            },
            {
                "address": 'module.openstack.openstack_compute_instance_v2.node["node2"]',
                "type": "openstack_compute_instance_v2",
                "change": {"actions": ["create"], "done": True},
            },
            {
                "address": 'module.openstack.openstack_compute_instance_v2.node["node3"]',
                "type": "openstack_compute_instance_v2",
                "change": {"actions": ["create"], "done": True},
            },
            {
                "address": "module.openstack.openstack_compute_keypair_v2.keypair",
                "type": "openstack_compute_keypair_v2",
                "change": {"actions": ["create"], "done": True},
            },
            {
                "address": "module.openstack.openstack_compute_secgroup_v2.secgroup_1",
                "type": "openstack_compute_secgroup_v2",
                "change": {"actions": ["create"], "done": True},
            },
            {
                "address": "module.openstack.openstack_compute_volume_attach_v2.va_home[0]",
                "type": "openstack_compute_volume_attach_v2",
                "change": {"actions": ["create"], "done": True},
            },
            {
                "address": "module.openstack.openstack_compute_volume_attach_v2.va_project[0]",
                "type": "openstack_compute_volume_attach_v2",
                "change": {"actions": ["create"], "done": True},
            },
            {
                "address": "module.openstack.openstack_compute_volume_attach_v2.va_scratch[0]",
                "type": "openstack_compute_volume_attach_v2",
                "change": {"actions": ["create"], "done": True},
            },
            {
                "address": "module.openstack.openstack_networking_floatingip_v2.fip[0]",
                "type": "openstack_networking_floatingip_v2",
                "change": {"actions": ["create"], "done": False},
            },
            {
                "address": "module.openstack.openstack_networking_port_v2.port_login[0]",
                "type": "openstack_networking_port_v2",
                "change": {"actions": ["create"], "done": True},
            },
            {
                "address": "module.openstack.openstack_networking_port_v2.port_mgmt[0]",
                "type": "openstack_networking_port_v2",
                "change": {"actions": ["create"], "done": True},
            },
            {
                "address": 'module.openstack.openstack_networking_port_v2.port_node["node1"]',
                "type": "openstack_networking_port_v2",
                "change": {"actions": ["create"], "done": True},
            },
            {
                "address": 'module.openstack.openstack_networking_port_v2.port_node["node2"]',
                "type": "openstack_networking_port_v2",
                "change": {"actions": ["create"], "done": True},
            },
            {
                "address": 'module.openstack.openstack_networking_port_v2.port_node["node3"]',
                "type": "openstack_networking_port_v2",
                "change": {"actions": ["create"], "done": True},
            },
            {
                "address": "module.openstack.random_pet.guest_passwd[0]",
                "type": "random_pet",
                "change": {"actions": ["create"], "done": True},
            },
            {
                "address": "module.openstack.random_string.freeipa_passwd",
                "type": "random_string",
                "change": {"actions": ["create"], "done": True},
            },
            {
                "address": "module.openstack.random_string.munge_key",
                "type": "random_string",
                "change": {"actions": ["create"], "done": True},
            },
            {
                "address": "module.openstack.random_string.puppetmaster_password",
                "type": "random_string",
                "change": {"actions": ["create"], "done": True},
            },
            {
                "address": "module.openstack.random_uuid.consul_token",
                "type": "random_uuid",
                "change": {"actions": ["create"], "done": True},
            },
            {
                "address": "module.openstack.tls_private_key.login_rsa",
                "type": "tls_private_key",
                "change": {"actions": ["create"], "done": True},
            },
        ],
    }


def test_get_status_code(client):
    res = client.get(f"/api/magic-castle/{NON_EXISTING_HOSTNAME}/status")
    assert res.get_json()["status"] == "not_found"

    modify_cluster_status(EXISTING_HOSTNAME, ClusterStatusCode.BUILD_RUNNING)
    res = client.get(f"/api/magic-castle/{EXISTING_HOSTNAME}/status")
    assert res.get_json()["status"] == "build_running"

    modify_cluster_status(EXISTING_HOSTNAME, ClusterStatusCode.BUILD_SUCCESS)
    res = client.get(f"/api/magic-castle/{EXISTING_HOSTNAME}/status")
    assert res.get_json()["status"] == "build_success"

    modify_cluster_status(EXISTING_HOSTNAME, ClusterStatusCode.BUILD_ERROR)
    res = client.get(f"/api/magic-castle/{EXISTING_HOSTNAME}/status")
    assert res.get_json()["status"] == "build_error"

    modify_cluster_status(EXISTING_HOSTNAME, ClusterStatusCode.DESTROY_RUNNING)
    res = client.get(f"/api/magic-castle/{EXISTING_HOSTNAME}/status")
    assert res.get_json()["status"] == "destroy_running"

    modify_cluster_status(EXISTING_HOSTNAME, ClusterStatusCode.DESTROY_ERROR)
    res = client.get(f"/api/magic-castle/{EXISTING_HOSTNAME}/status")
    assert res.get_json()["status"] == "destroy_error"

    modify_cluster_status(EXISTING_HOSTNAME, ClusterStatusCode.IDLE)
    res = client.get(f"/api/magic-castle/{EXISTING_HOSTNAME}/status")
    assert res.get_json()["status"] == "idle"


# DELETE /api/magic-castle/<hostname>
def test_delete_invalid_status(client):
    res = client.delete(f"/api/magic-castle/{NON_EXISTING_HOSTNAME}")
    assert res.get_json() == {"message": "This cluster does not exist"}
    assert res.status_code != 200

    modify_cluster_status(EXISTING_HOSTNAME, ClusterStatusCode.DESTROY_RUNNING)
    res = client.delete(f"/api/magic-castle/{EXISTING_HOSTNAME}")
    assert res.get_json() == {"message": "This cluster is busy"}
    assert res.status_code != 200

    modify_cluster_status(EXISTING_HOSTNAME, ClusterStatusCode.BUILD_RUNNING)
    res = client.delete(f"/api/magic-castle/{EXISTING_HOSTNAME}")
    assert res.get_json() == {"message": "This cluster is busy"}
    assert res.status_code != 200


# PUT /api/magic-castle/<hostname>
def test_modify_invalid_status(client):
    res = client.put(
        f"/api/magic-castle/{NON_EXISTING_HOSTNAME}",
        json=NON_EXISTING_CLUSTER_CONFIGURATION,
    )
    assert res.get_json() == {"message": "This cluster does not exist"}
    assert res.status_code != 200

    modify_cluster_status(EXISTING_HOSTNAME, ClusterStatusCode.BUILD_RUNNING)
    res = client.put(
        f"/api/magic-castle/{EXISTING_HOSTNAME}", json=EXISTING_CLUSTER_CONFIGURATION,
    )
    assert res.get_json() == {"message": "This cluster is busy"}
    assert res.status_code != 200

    modify_cluster_status(EXISTING_HOSTNAME, ClusterStatusCode.DESTROY_RUNNING)
    res = client.put(
        f"/api/magic-castle/{EXISTING_HOSTNAME}", json=EXISTING_CLUSTER_CONFIGURATION,
    )
    assert res.get_json() == {"message": "This cluster is busy"}
    assert res.status_code != 200


def modify_cluster_status(hostname, status: ClusterStatusCode):
    with open(
        path.join(MOCK_CLUSTERS_PATH, hostname, "status.txt"), "w"
    ) as status_file:
        status_file.write(status.value)
