from models.magic_castle import MagicCastle
from models.terraform_plan_parser import TerraformPlanParser
from pathlib import Path
from os import path
import pytest
import json
from tests.test_helpers import *


def load_plan(hostname):
    state_file_path = path.join(
        Path(__file__).parent.parent,
        "mock-clusters",
        hostname,
        f"terraform_plan.json",
    )
    with open(state_file_path, "r") as terraform_state_file:
        return json.load(terraform_state_file)


def read_terraform_apply_log(hostname):
    terraform_apply_output_path = path.join(
        Path(__file__).parent.parent,
        "mock-clusters",
        hostname,
        f"terraform_apply.log",
    )
    with open(terraform_apply_output_path, "r") as terraform_apply_output_file:
        return terraform_apply_output_file.read()


@pytest.fixture
def missing_floating_ips_initial_plan():
    return load_plan("missingfloatingips.c3.ca")


def test_get_resources_changes_missing_floating_ips_intial(
    missing_floating_ips_initial_plan,
):
    assert TerraformPlanParser.get_resources_changes(
        missing_floating_ips_initial_plan
    ) == [
        {
            "address": "module.openstack.data.template_cloudinit_config.login_config[0]",
            "type": "template_cloudinit_config",
            "change": {"actions": ["read"],},
        },
        {
            "address": "module.openstack.data.template_cloudinit_config.mgmt_config[0]",
            "type": "template_cloudinit_config",
            "change": {"actions": ["read"],},
        },
        {
            "address": 'module.openstack.data.template_cloudinit_config.node_config["node1"]',
            "type": "template_cloudinit_config",
            "change": {"actions": ["read"],},
        },
        {
            "address": 'module.openstack.data.template_cloudinit_config.node_config["node2"]',
            "type": "template_cloudinit_config",
            "change": {"actions": ["read"],},
        },
        {
            "address": 'module.openstack.data.template_cloudinit_config.node_config["node3"]',
            "type": "template_cloudinit_config",
            "change": {"actions": ["read"],},
        },
        {
            "address": "module.openstack.data.template_file.hieradata",
            "type": "template_file",
            "change": {"actions": ["read"],},
        },
        {
            "address": "module.openstack.openstack_blockstorage_volume_v2.home[0]",
            "type": "openstack_blockstorage_volume_v2",
            "change": {"actions": ["create"],},
        },
        {
            "address": "module.openstack.openstack_blockstorage_volume_v2.project[0]",
            "type": "openstack_blockstorage_volume_v2",
            "change": {"actions": ["create"],},
        },
        {
            "address": "module.openstack.openstack_blockstorage_volume_v2.scratch[0]",
            "type": "openstack_blockstorage_volume_v2",
            "change": {"actions": ["create"],},
        },
        {
            "address": "module.openstack.openstack_compute_floatingip_associate_v2.fip[0]",
            "type": "openstack_compute_floatingip_associate_v2",
            "change": {"actions": ["create"],},
        },
        {
            "address": "module.openstack.openstack_compute_instance_v2.login[0]",
            "type": "openstack_compute_instance_v2",
            "change": {"actions": ["create"],},
        },
        {
            "address": "module.openstack.openstack_compute_instance_v2.mgmt[0]",
            "type": "openstack_compute_instance_v2",
            "change": {"actions": ["create"],},
        },
        {
            "address": 'module.openstack.openstack_compute_instance_v2.node["node1"]',
            "type": "openstack_compute_instance_v2",
            "change": {"actions": ["create"],},
        },
        {
            "address": 'module.openstack.openstack_compute_instance_v2.node["node2"]',
            "type": "openstack_compute_instance_v2",
            "change": {"actions": ["create"],},
        },
        {
            "address": 'module.openstack.openstack_compute_instance_v2.node["node3"]',
            "type": "openstack_compute_instance_v2",
            "change": {"actions": ["create"],},
        },
        {
            "address": "module.openstack.openstack_compute_keypair_v2.keypair",
            "type": "openstack_compute_keypair_v2",
            "change": {"actions": ["create"],},
        },
        {
            "address": "module.openstack.openstack_compute_secgroup_v2.secgroup_1",
            "type": "openstack_compute_secgroup_v2",
            "change": {"actions": ["create"],},
        },
        {
            "address": "module.openstack.openstack_compute_volume_attach_v2.va_home[0]",
            "type": "openstack_compute_volume_attach_v2",
            "change": {"actions": ["create"],},
        },
        {
            "address": "module.openstack.openstack_compute_volume_attach_v2.va_project[0]",
            "type": "openstack_compute_volume_attach_v2",
            "change": {"actions": ["create"],},
        },
        {
            "address": "module.openstack.openstack_compute_volume_attach_v2.va_scratch[0]",
            "type": "openstack_compute_volume_attach_v2",
            "change": {"actions": ["create"],},
        },
        {
            "address": "module.openstack.openstack_networking_floatingip_v2.fip[0]",
            "type": "openstack_networking_floatingip_v2",
            "change": {"actions": ["create"],},
        },
        {
            "address": "module.openstack.openstack_networking_port_v2.port_login[0]",
            "type": "openstack_networking_port_v2",
            "change": {"actions": ["create"],},
        },
        {
            "address": "module.openstack.openstack_networking_port_v2.port_mgmt[0]",
            "type": "openstack_networking_port_v2",
            "change": {"actions": ["create"],},
        },
        {
            "address": 'module.openstack.openstack_networking_port_v2.port_node["node1"]',
            "type": "openstack_networking_port_v2",
            "change": {"actions": ["create"],},
        },
        {
            "address": 'module.openstack.openstack_networking_port_v2.port_node["node2"]',
            "type": "openstack_networking_port_v2",
            "change": {"actions": ["create"],},
        },
        {
            "address": 'module.openstack.openstack_networking_port_v2.port_node["node3"]',
            "type": "openstack_networking_port_v2",
            "change": {"actions": ["create"],},
        },
        {
            "address": "module.openstack.random_pet.guest_passwd[0]",
            "type": "random_pet",
            "change": {"actions": ["create"],},
        },
        {
            "address": "module.openstack.random_string.freeipa_passwd",
            "type": "random_string",
            "change": {"actions": ["create"],},
        },
        {
            "address": "module.openstack.random_string.munge_key",
            "type": "random_string",
            "change": {"actions": ["create"],},
        },
        {
            "address": "module.openstack.random_string.puppetmaster_password",
            "type": "random_string",
            "change": {"actions": ["create"],},
        },
        {
            "address": "module.openstack.random_uuid.consul_token",
            "type": "random_uuid",
            "change": {"actions": ["create"],},
        },
        {
            "address": "module.openstack.tls_private_key.login_rsa",
            "type": "tls_private_key",
            "change": {"actions": ["create"]},
        },
    ]


def test_get_done_changes(missing_floating_ips_initial_plan):
    assert TerraformPlanParser.get_done_changes(
        missing_floating_ips_initial_plan,
        read_terraform_apply_log("missingfloatingips.c3.ca"),
    ) == [
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
    ]
