NON_EXISTING_CLUSTER_CONFIGURATION = {
    "cluster_name": "nonexisting",
    "domain": "calculquebec.cloud",
    "image": "CentOS-7-x64-2021-11",
    "nb_users": 10,
    "instances": {
        "mgmt": {"type": "p4-6gb", "count": 1, "tags": ["mgmt", "nfs", "puppet"]},
        "login": {"type": "p4-6gb", "count": 1, "tags": ["login", "proxy", "public"]},
        "node": {"type": "p2-3gb", "count": 1, "tags": ["node"]},
    },
    "volumes": {
        "nfs": {
            "home": {"size": 100},
            "project": {"size": 50},
            "scratch": {"size": 50},
        }
    },
    "public_keys": [],
    "guest_passwd": "",
    "hieradata": "",
}

EXISTING_CLUSTER_CONFIGURATION = {
    "cluster_name": "valid1",
    "domain": "calculquebec.cloud",
    "image": "CentOS-7-x64-2021-11",
    "nb_users": 10,
    "instances": {
        "mgmt": {"type": "p4-6gb", "count": 1, "tags": ["mgmt", "nfs", "puppet"]},
        "login": {"type": "p4-6gb", "count": 1, "tags": ["login", "proxy", "public"]},
        "node": {"type": "p2-3gb", "count": 1, "tags": ["node"]},
    },
    "volumes": {
        "nfs": {
            "home": {"size": 100},
            "project": {"size": 50},
            "scratch": {"size": 50},
        }
    },
    "public_keys": [],
    "guest_passwd": "",
    "hieradata": "",
}

NON_EXISTING_HOSTNAME = f"{NON_EXISTING_CLUSTER_CONFIGURATION['cluster_name']}.{NON_EXISTING_CLUSTER_CONFIGURATION['domain']}"
EXISTING_HOSTNAME = f"{EXISTING_CLUSTER_CONFIGURATION['cluster_name']}.{EXISTING_CLUSTER_CONFIGURATION['domain']}"

EXISTING_CLUSTER_STATE = {
    **EXISTING_CLUSTER_CONFIGURATION,
    "cloud": {"id": 1, "name": "project-alice"},
    "guest_passwd": "password-123",
    "public_keys": ["ssh-rsa FAKE"],
    "status": "provisioning_success",
    "hostname": "valid1.calculquebec.cloud",
    "freeipa_passwd": "FAKE",
    "expiration_date": "2029-01-01",
}

IGNORE_FIELDS = ["age"]

ALICE_HEADERS = {
    "eduPersonPrincipalName": "alice@computecanada.ca",
    "givenName": "Alice",
    "surname": "Tremblay",
    "mail": "alice.tremblay@example.com",
    "sshPublicKey": "ssh-rsa FAKE",
}

BOB_HEADERS = {
    "eduPersonPrincipalName": "bob12.bobby@computecanada.ca",
    "givenName": "Bob",
    "surname": "Rodriguez",
    "mail": "bob-rodriguez435@example.com",
    "sshPublicKey": "ssh-rsa FAKE",
}

CLUSTERS = {
    "buildplanning.calculquebec.cloud": {
        "cloud": {"id": 1, "name": "project-alice"},
        "cluster_name": "buildplanning",
        "domain": "calculquebec.cloud",
        "expiration_date": "2029-01-01",
        "image": "CentOS-7-x64-2021-11",
        "nb_users": 34,
        "instances": {
            "mgmt": {
                "type": "c2-7.5gb-31",
                "count": 1,
                "tags": ["mgmt", "nfs", "puppet"],
            },
            "login": {
                "type": "p4-6gb",
                "count": 1,
                "tags": ["login", "proxy", "public"],
            },
            "node": {"type": "c1-7.5gb-30", "count": 5, "tags": ["node"]},
        },
        "volumes": {
            "nfs": {
                "home": {"size": 73},
                "project": {"size": 1},
                "scratch": {"size": 1},
            }
        },
        "public_keys": ["ssh-rsa FAKE"],
        "guest_passwd": "password-123",
        "hieradata": "",
        "hostname": "buildplanning.calculquebec.cloud",
        "status": "plan_running",
        "freeipa_passwd": None,
    },
    "created.calculquebec.cloud": {
        "cloud": {"id": 1, "name": "project-alice"},
        "cluster_name": "created",
        "domain": "calculquebec.cloud",
        "expiration_date": "2029-01-01",
        "image": "CentOS-7-x64-2021-11",
        "nb_users": 34,
        "instances": {
            "mgmt": {
                "type": "c2-7.5gb-31",
                "count": 1,
                "tags": ["mgmt", "nfs", "puppet"],
            },
            "login": {
                "type": "p4-6gb",
                "count": 1,
                "tags": ["login", "proxy", "public"],
            },
            "node": {"type": "c1-7.5gb-30", "count": 5, "tags": ["node"]},
        },
        "volumes": {
            "nfs": {
                "home": {"size": 73},
                "project": {"size": 1},
                "scratch": {"size": 1},
            }
        },
        "public_keys": ["ssh-rsa FAKE"],
        "guest_passwd": "password-123",
        "hieradata": "",
        "hostname": "created.calculquebec.cloud",
        "status": "created",
        "freeipa_passwd": None,
    },
    "valid1.calculquebec.cloud": {
        "cloud": {"id": 1, "name": "project-alice"},
        "cluster_name": "valid1",
        "domain": "calculquebec.cloud",
        "expiration_date": "2029-01-01",
        "image": "CentOS-7-x64-2021-11",
        "nb_users": 10,
        "instances": {
            "mgmt": {
                "type": "p4-6gb",
                "count": 1,
                "tags": ["mgmt", "nfs", "puppet"],
            },
            "login": {
                "type": "p4-6gb",
                "count": 1,
                "tags": ["login", "proxy", "public"],
            },
            "node": {"type": "p2-3gb", "count": 1, "tags": ["node"]},
        },
        "volumes": {
            "nfs": {
                "home": {"size": 100},
                "project": {"size": 50},
                "scratch": {"size": 50},
            }
        },
        "public_keys": ["ssh-rsa FAKE"],
        "guest_passwd": "password-123",
        "hieradata": "",
        "hostname": "valid1.calculquebec.cloud",
        "status": "provisioning_success",
        "freeipa_passwd": "FAKE",
    },
    "empty-state.calculquebec.cloud": {
        "cloud": {"id": 2, "name": "project-bob"},
        "hostname": "empty-state.calculquebec.cloud",
        "cluster_name": "empty-state",
        "domain": "calculquebec.cloud",
        "expiration_date": "2029-01-01",
        "image": "CentOS-7-x64-2021-11",
        "nb_users": 34,
        "instances": {
            "mgmt": {
                "type": "c2-7.5gb-31",
                "count": 1,
                "tags": ["mgmt", "nfs", "puppet"],
            },
            "login": {
                "type": "p4-6gb",
                "count": 1,
                "tags": ["login", "proxy", "public"],
            },
            "node": {"type": "c1-7.5gb-30", "count": 5, "tags": ["node"]},
        },
        "volumes": {
            "nfs": {
                "home": {"size": 73},
                "project": {"size": 1},
                "scratch": {"size": 1},
            }
        },
        "public_keys": ["ssh-rsa FAKE"],
        "guest_passwd": "password-123",
        "hieradata": "",
        "status": "build_error",
        "freeipa_passwd": None,
    },
    "empty.calculquebec.cloud": {
        "cloud": {"id": 2, "name": "project-bob"},
        "hostname": "empty.calculquebec.cloud",
        "status": "build_error",
        "freeipa_passwd": None,
        "expiration_date": "2029-01-01",
    },
    "missingfloatingips.c3.ca": {
        "cloud": {"id": 2, "name": "project-bob"},
        "cluster_name": "missingfloatingips",
        "domain": "c3.ca",
        "expiration_date": "2029-01-01",
        "image": "CentOS-7-x64-2021-11",
        "nb_users": 17,
        "instances": {
            "mgmt": {
                "type": "p4-6gb",
                "count": 1,
                "tags": ["mgmt", "nfs", "puppet"],
            },
            "login": {
                "type": "p4-6gb",
                "count": 1,
                "tags": ["login", "proxy", "public"],
            },
            "node": {"type": "p2-3gb", "count": 3, "tags": ["node"]},
        },
        "volumes": {
            "nfs": {
                "home": {"size": 50},
                "project": {"size": 1},
                "scratch": {"size": 1},
            }
        },
        "public_keys": ["ssh-rsa FAKE"],
        "guest_passwd": "password-123",
        "hieradata": "",
        "hostname": "missingfloatingips.c3.ca",
        "status": "build_running",
        "freeipa_passwd": None,
    },
    "missingnodes.c3.ca": {
        "cloud": {"id": 2, "name": "project-bob"},
        "cluster_name": "missingnodes",
        "domain": "c3.ca",
        "expiration_date": "2029-01-01",
        "image": "CentOS-7-x64-2021-11",
        "nb_users": 10,
        "instances": {
            "mgmt": {
                "type": "p4-6gb",
                "count": 1,
                "tags": ["mgmt", "nfs", "puppet"],
            },
            "login": {
                "type": "p4-6gb",
                "count": 1,
                "tags": ["login", "proxy", "public"],
            },
            "node": {"type": "p2-3gb", "count": 1, "tags": ["node"]},
        },
        "volumes": {
            "nfs": {
                "home": {"size": 100},
                "project": {"size": 50},
                "scratch": {"size": 50},
            }
        },
        "public_keys": ["ssh-rsa FAKE"],
        "guest_passwd": "password-123",
        "hieradata": "",
        "hostname": "missingnodes.c3.ca",
        "status": "build_error",
        "freeipa_passwd": "FAKE",
    },
    "noowner.calculquebec.cloud": {
        "cloud": {"id": 2, "name": "project-bob"},
        "cluster_name": "noowner",
        "domain": "calculquebec.cloud",
        "expiration_date": "2029-01-01",
        "image": "CentOS-7-x64-2021-11",
        "nb_users": 10,
        "instances": {
            "mgmt": {
                "type": "p4-6gb",
                "count": 1,
                "tags": ["mgmt", "nfs", "puppet"],
            },
            "login": {
                "type": "p4-6gb",
                "count": 1,
                "tags": ["login", "proxy", "public"],
            },
            "node": {"type": "p2-3gb", "count": 1, "tags": ["node"]},
        },
        "volumes": {
            "nfs": {
                "home": {"size": 100},
                "project": {"size": 50},
                "scratch": {"size": 50},
            }
        },
        "public_keys": ["ssh-rsa FAKE"],
        "guest_passwd": "password-123",
        "hieradata": "",
        "hostname": "noowner.calculquebec.cloud",
        "status": "provisioning_success",
        "freeipa_passwd": "FAKE",
    },
}

PROGRESS_DATA = {
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
