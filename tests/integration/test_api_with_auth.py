import pytest

from mchub.models.magic_castle.cluster_status_code import ClusterStatusCode
from mchub import create_app

from ..test_helpers import *  # noqa;
from ..mocks.configuration.config_mock import config_auth_saml_mock  # noqa;
from ..data import (
    NON_EXISTING_CLUSTER_CONFIGURATION,
    EXISTING_CLUSTER_CONFIGURATION,
    IGNORE_FIELDS,
    EXISTING_HOSTNAME,
    NON_EXISTING_HOSTNAME,
    EXISTING_CLUSTER_STATE,
    ALICE_HEADERS,
    BOB_HEADERS,
    CLUSTERS,
)


# GET /api/users/me
def test_get_current_user_authentified(client):
    res = client.get(f"/api/users/me", headers=ALICE_HEADERS)
    assert res.get_json() == {
        "username": "alice",
        "usertype": "saml",
        "public_keys": ["ssh-rsa FAKE"],
    }
    res = client.get(f"/api/users/me", headers=BOB_HEADERS)
    assert res.get_json() == {
        "username": "bob12.bobby",
        "usertype": "saml",
        "public_keys": ["ssh-rsa FAKE"],
    }


# GET /api/users/me
def test_get_current_user_non_authentified(client):
    res = client.get(f"/api/users/me")
    assert res.get_json() == {"message": "You need to be authenticated."}


# GET /api/magic_castle
def test_get_all_magic_castle_names(client):
    res = client.get(f"/api/magic-castles", headers=ALICE_HEADERS)
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
    assert res.status_code == 200


def test_query_magic_castles_local(client):
    # No authentication header at all
    res = client.get(f"/api/magic-castles")
    assert res.get_json() == {"message": "You need to be authenticated."}
    assert res.status_code != 200

    # Missing some authentication headers
    res = client.get(
        f"/api/magic-castles",
        headers={"eduPersonPrincipalName": "alice@computecanada.ca"},
    )
    assert res.get_json() == {"message": "You need to be authenticated."}
    assert res.status_code != 200


# GET /api/magic-castles/<hostname>
def test_get_state_existing(client):
    res = client.get(f"/api/magic-castles/{EXISTING_HOSTNAME}", headers=ALICE_HEADERS)
    state = res.get_json()
    for field in IGNORE_FIELDS:
        state.pop(field)
    assert state == EXISTING_CLUSTER_STATE
    assert res.status_code == 200


def test_get_state_non_existing(client):
    res = client.get(
        f"/api/magic-castles/{NON_EXISTING_HOSTNAME}", headers=ALICE_HEADERS
    )
    assert res.get_json() == {"message": "This cluster does not exist."}
    assert res.status_code != 200


def test_get_state_not_owned(client):
    res = client.get(
        f"/api/magic-castles/missingfloatingips.c3.ca", headers=ALICE_HEADERS
    )
    assert res.get_json() == {"message": "This cluster does not exist."}
    assert res.status_code != 200


# GET /api/magic-castles/<hostname>/status
@pytest.mark.skip(reason="source of truth is currently false")
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


def test_get_status_code(client):
    res = client.get(
        f"/api/magic-castles/{NON_EXISTING_HOSTNAME}/status", headers=ALICE_HEADERS
    )
    assert res.get_json()["status"] == "not_found"

    orm = MagicCastleORM.query.filter_by(hostname=EXISTING_HOSTNAME).first()
    orm.status = ClusterStatusCode.BUILD_RUNNING
    db.session.commit()
    res = client.get(
        f"/api/magic-castles/{EXISTING_HOSTNAME}/status", headers=ALICE_HEADERS
    )
    assert res.get_json()["status"] == "build_running"

    orm = MagicCastleORM.query.filter_by(hostname=EXISTING_HOSTNAME).first()
    orm.status = ClusterStatusCode.PROVISIONING_SUCCESS
    db.session.commit()
    res = client.get(
        f"/api/magic-castles/{EXISTING_HOSTNAME}/status", headers=ALICE_HEADERS
    )
    assert res.get_json()["status"] == "provisioning_success"

    orm = MagicCastleORM.query.filter_by(hostname=EXISTING_HOSTNAME).first()
    orm.status = ClusterStatusCode.BUILD_ERROR
    db.session.commit()
    res = client.get(
        f"/api/magic-castles/{EXISTING_HOSTNAME}/status", headers=ALICE_HEADERS
    )
    assert res.get_json()["status"] == "build_error"

    orm = MagicCastleORM.query.filter_by(hostname=EXISTING_HOSTNAME).first()
    orm.status = ClusterStatusCode.DESTROY_RUNNING
    db.session.commit()
    res = client.get(
        f"/api/magic-castles/{EXISTING_HOSTNAME}/status", headers=ALICE_HEADERS
    )
    assert res.get_json()["status"] == "destroy_running"

    orm = MagicCastleORM.query.filter_by(hostname=EXISTING_HOSTNAME).first()
    orm.status = ClusterStatusCode.DESTROY_ERROR
    db.session.commit()
    res = client.get(
        f"/api/magic-castles/{EXISTING_HOSTNAME}/status", headers=ALICE_HEADERS
    )
    assert res.get_json()["status"] == "destroy_error"


# DELETE /api/magic-castles/<hostname>
def test_delete_invalid_status(client):
    res = client.delete(
        f"/api/magic-castles/{NON_EXISTING_HOSTNAME}", headers=ALICE_HEADERS
    )
    assert res.get_json() == {"message": "This cluster does not exist."}
    assert res.status_code != 200

    orm = MagicCastleORM.query.filter_by(hostname=EXISTING_HOSTNAME).first()
    orm.status = ClusterStatusCode.DESTROY_RUNNING
    db.session.commit()
    res = client.delete(
        f"/api/magic-castles/{EXISTING_HOSTNAME}", headers=ALICE_HEADERS
    )
    assert res.get_json() == {"message": "This cluster is busy."}
    assert res.status_code != 200

    orm = MagicCastleORM.query.filter_by(hostname=EXISTING_HOSTNAME).first()
    orm.status = ClusterStatusCode.BUILD_RUNNING
    db.session.commit()
    res = client.delete(
        f"/api/magic-castles/{EXISTING_HOSTNAME}", headers=ALICE_HEADERS
    )
    assert res.get_json() == {"message": "This cluster is busy."}
    assert res.status_code != 200


# PUT /api/magic-castles/<hostname>
def test_modify_invalid_status(client):
    res = client.put(
        f"/api/magic-castles/{NON_EXISTING_HOSTNAME}",
        json=NON_EXISTING_CLUSTER_CONFIGURATION,
        headers=ALICE_HEADERS,
    )
    assert res.get_json() == {"message": "This cluster does not exist."}
    assert res.status_code != 200

    orm = MagicCastleORM.query.filter_by(hostname=EXISTING_HOSTNAME).first()
    orm.status = ClusterStatusCode.BUILD_RUNNING
    db.session.commit()
    res = client.put(
        f"/api/magic-castles/{EXISTING_HOSTNAME}",
        json=EXISTING_CLUSTER_CONFIGURATION,
        headers=ALICE_HEADERS,
    )
    assert res.get_json() == {"message": "This cluster is busy."}
    assert res.status_code != 200

    orm = MagicCastleORM.query.filter_by(hostname=EXISTING_HOSTNAME).first()
    orm.status = ClusterStatusCode.DESTROY_RUNNING
    db.session.commit()
    res = client.put(
        f"/api/magic-castles/{EXISTING_HOSTNAME}",
        json=EXISTING_CLUSTER_CONFIGURATION,
        headers=ALICE_HEADERS,
    )
    assert res.get_json() == {"message": "This cluster is busy."}
    assert res.status_code != 200
