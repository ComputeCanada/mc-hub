from mchub.models.magic_castle.plan_type import PlanType

DEFAULT_TEMPLATE = {
    "cloud": {"id": None, "name": None},
    "cluster_name": "",
    "domain": None,
    "image": None,
    "nb_users": 10,
    "instances": {
        "mgmt": {"type": None, "count": 1, "tags": ["mgmt", "nfs", "puppet"]},
        "login": {"type": None, "count": 1, "tags": ["login", "proxy", "public"]},
        "node": {"type": None, "count": 1, "tags": ["node"]},
    },
    "volumes": {
        "nfs": {
            "home": {"size": 100},
            "project": {"size": 100},
            "scratch": {"size": 100},
        }
    },
    "public_keys": [],
    "guest_passwd": "",
    "hieradata": "",
}

NON_EXISTING_CLUSTER_CONFIGURATION = {
    "cluster_name": "nonexisting",
    "domain": "magic-castle.cloud",
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
    "domain": "magic-castle.cloud",
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
    "hostname": "valid1.magic-castle.cloud",
    "freeipa_passwd": "FAKE",
    "expiration_date": "2029-01-01",
    "age": "a moment",
}

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

PLAN_TYPE = {
    "buildplanning.magic-castle.cloud": PlanType.BUILD,
    "created.magic-castle.cloud": PlanType.BUILD,
    "valid1.magic-castle.cloud": PlanType.DESTROY,
    "empty-state.magic-castle.cloud": None,
    "missingfloatingips.mc.ca": None,
    "missingnodes.mc.ca": None,
    "noowner.magic-castle.cloud": None,
}

CLUSTERS_CONFIG = {
    "buildplanning.magic-castle.cloud": {
        "cluster_name": "buildplanning",
        "domain": "magic-castle.cloud",
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
    },
    "created.magic-castle.cloud": {
        "cluster_name": "created",
        "domain": "magic-castle.cloud",
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
    },
    "valid1.magic-castle.cloud": {
        "cluster_name": "valid1",
        "domain": "magic-castle.cloud",
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
    },
    "empty-state.magic-castle.cloud": {
        "cluster_name": "empty-state",
        "domain": "magic-castle.cloud",
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
    },
    "missingfloatingips.mc.ca": {
        "cluster_name": "missingfloatingips",
        "domain": "mc.ca",
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
    },
    "missingnodes.mc.ca": {
        "cluster_name": "missingnodes",
        "domain": "mc.ca",
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
    },
    "noowner.magic-castle.cloud": {
        "cluster_name": "noowner",
        "domain": "magic-castle.cloud",
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
    },
}

CLUSTERS = {
    "buildplanning.magic-castle.cloud": {
        **CLUSTERS_CONFIG["buildplanning.magic-castle.cloud"],
        "cloud": {"id": 1, "name": "project-alice"},
        "expiration_date": "2029-01-01",
        "hostname": "buildplanning.magic-castle.cloud",
        "status": "plan_running",
        "freeipa_passwd": None,
        "age": "a moment",
    },
    "created.magic-castle.cloud": {
        **CLUSTERS_CONFIG["created.magic-castle.cloud"],
        "cloud": {"id": 1, "name": "project-alice"},
        "expiration_date": "2029-01-01",
        "hostname": "created.magic-castle.cloud",
        "status": "created",
        "freeipa_passwd": None,
        "age": "a moment",
    },
    "valid1.magic-castle.cloud": {
        **CLUSTERS_CONFIG["valid1.magic-castle.cloud"],
        "cloud": {"id": 1, "name": "project-alice"},
        "expiration_date": "2029-01-01",
        "hostname": "valid1.magic-castle.cloud",
        "status": "provisioning_success",
        "freeipa_passwd": "FAKE",
        "age": "a moment",
    },
    "empty-state.magic-castle.cloud": {
        **CLUSTERS_CONFIG["empty-state.magic-castle.cloud"],
        "cloud": {"id": 2, "name": "project-bob"},
        "hostname": "empty-state.magic-castle.cloud",
        "expiration_date": "2029-01-01",
        "status": "build_error",
        "freeipa_passwd": None,
        "age": "a moment",
    },
    "missingfloatingips.mc.ca": {
        **CLUSTERS_CONFIG["missingfloatingips.mc.ca"],
        "cloud": {"id": 2, "name": "project-bob"},
        "hostname": "missingfloatingips.mc.ca",
        "expiration_date": "2029-01-01",
        "status": "build_running",
        "freeipa_passwd": None,
        "age": "a moment",
    },
    "missingnodes.mc.ca": {
        **CLUSTERS_CONFIG["missingnodes.mc.ca"],
        "cloud": {"id": 2, "name": "project-bob"},
        "hostname": "missingnodes.mc.ca",
        "expiration_date": "2029-01-01",
        "status": "build_error",
        "freeipa_passwd": "FAKE",
        "age": "a moment",
    },
    "noowner.magic-castle.cloud": {
        **CLUSTERS_CONFIG["noowner.magic-castle.cloud"],
        "cloud": {"id": 2, "name": "project-bob"},
        "hostname": "noowner.magic-castle.cloud",
        "expiration_date": "2029-01-01",
        "status": "provisioning_success",
        "freeipa_passwd": "FAKE",
        "age": "a moment",
    },
}

PROGRESS_DATA = {
    "status": "build_running",
    "stateful": False,
    "progress": [
        {
            "address": "module.openstack.module.cluster_config.null_resource.deploy_hieradata[0]",
            "type": "null_resource",
            "change": {"actions": ["create"], "progress": "queued"},
        },
        {
            "address": "module.openstack.module.cluster_config.random_string.freeipa_passwd",
            "type": "random_string",
            "change": {"actions": ["create"], "progress": "queued"},
        },
        {
            "address": "module.openstack.module.cluster_config.random_string.munge_key",
            "type": "random_string",
            "change": {"actions": ["create"], "progress": "queued"},
        },
        {
            "address": "module.openstack.module.cluster_config.random_uuid.consul_token",
            "type": "random_uuid",
            "change": {"actions": ["create"], "progress": "queued"},
        },
        {
            "address": "module.openstack.module.instance_config.random_string.puppetserver_password",
            "type": "random_string",
            "change": {"actions": ["create"], "progress": "queued"},
        },
        {
            "address": 'module.openstack.module.instance_config.tls_private_key.rsa_hostkeys["login"]',
            "type": "tls_private_key",
            "change": {"actions": ["create"], "progress": "queued"},
        },
        {
            "address": 'module.openstack.module.instance_config.tls_private_key.rsa_hostkeys["mgmt"]',
            "type": "tls_private_key",
            "change": {"actions": ["create"], "progress": "queued"},
        },
        {
            "address": 'module.openstack.module.instance_config.tls_private_key.rsa_hostkeys["node"]',
            "type": "tls_private_key",
            "change": {"actions": ["create"], "progress": "queued"},
        },
        {
            "address": "module.openstack.module.instance_config.tls_private_key.ssh[0]",
            "type": "tls_private_key",
            "change": {"actions": ["create"], "progress": "queued"},
        },
        {
            "address": 'module.openstack.openstack_blockstorage_volume_v3.volumes["mgmt1-nfs-home"]',
            "type": "openstack_blockstorage_volume_v3",
            "change": {"actions": ["create"], "progress": "queued"},
        },
        {
            "address": 'module.openstack.openstack_blockstorage_volume_v3.volumes["mgmt1-nfs-project"]',
            "type": "openstack_blockstorage_volume_v3",
            "change": {"actions": ["create"], "progress": "queued"},
        },
        {
            "address": 'module.openstack.openstack_blockstorage_volume_v3.volumes["mgmt1-nfs-scratch"]',
            "type": "openstack_blockstorage_volume_v3",
            "change": {"actions": ["create"], "progress": "queued"},
        },
        {
            "address": 'module.openstack.openstack_compute_floatingip_associate_v2.fip["login1"]',
            "type": "openstack_compute_floatingip_associate_v2",
            "change": {"actions": ["create"], "progress": "queued"},
        },
        {
            "address": 'module.openstack.openstack_compute_instance_v2.instances["login1"]',
            "type": "openstack_compute_instance_v2",
            "change": {"actions": ["create"], "progress": "queued"},
        },
        {
            "address": 'module.openstack.openstack_compute_instance_v2.instances["mgmt1"]',
            "type": "openstack_compute_instance_v2",
            "change": {"actions": ["create"], "progress": "queued"},
        },
        {
            "address": 'module.openstack.openstack_compute_instance_v2.instances["node1"]',
            "type": "openstack_compute_instance_v2",
            "change": {"actions": ["create"], "progress": "queued"},
        },
        {
            "address": 'module.openstack.openstack_compute_instance_v2.instances["node2"]',
            "type": "openstack_compute_instance_v2",
            "change": {"actions": ["create"], "progress": "queued"},
        },
        {
            "address": 'module.openstack.openstack_compute_instance_v2.instances["node3"]',
            "type": "openstack_compute_instance_v2",
            "change": {"actions": ["create"], "progress": "queued"},
        },
        {
            "address": "module.openstack.openstack_compute_keypair_v2.keypair",
            "type": "openstack_compute_keypair_v2",
            "change": {"actions": ["create"], "progress": "done"},
        },
        {
            "address": "module.openstack.openstack_compute_secgroup_v2.secgroup",
            "type": "openstack_compute_secgroup_v2",
            "change": {"actions": ["create"], "progress": "queued"},
        },
        {
            "address": 'module.openstack.openstack_compute_volume_attach_v2.attachments["mgmt1-nfs-home"]',
            "type": "openstack_compute_volume_attach_v2",
            "change": {"actions": ["create"], "progress": "queued"},
        },
        {
            "address": 'module.openstack.openstack_compute_volume_attach_v2.attachments["mgmt1-nfs-project"]',
            "type": "openstack_compute_volume_attach_v2",
            "change": {"actions": ["create"], "progress": "queued"},
        },
        {
            "address": 'module.openstack.openstack_compute_volume_attach_v2.attachments["mgmt1-nfs-scratch"]',
            "type": "openstack_compute_volume_attach_v2",
            "change": {"actions": ["create"], "progress": "queued"},
        },
        {
            "address": 'module.openstack.openstack_networking_floatingip_v2.fip["login1"]',
            "type": "openstack_networking_floatingip_v2",
            "change": {"actions": ["create"], "progress": "queued"},
        },
        {
            "address": 'module.openstack.openstack_networking_port_v2.nic["login1"]',
            "type": "openstack_networking_port_v2",
            "change": {"actions": ["create"], "progress": "queued"},
        },
        {
            "address": 'module.openstack.openstack_networking_port_v2.nic["mgmt1"]',
            "type": "openstack_networking_port_v2",
            "change": {"actions": ["create"], "progress": "queued"},
        },
        {
            "address": 'module.openstack.openstack_networking_port_v2.nic["node1"]',
            "type": "openstack_networking_port_v2",
            "change": {"actions": ["create"], "progress": "queued"},
        },
        {
            "address": 'module.openstack.openstack_networking_port_v2.nic["node2"]',
            "type": "openstack_networking_port_v2",
            "change": {"actions": ["create"], "progress": "queued"},
        },
        {
            "address": 'module.openstack.openstack_networking_port_v2.nic["node3"]',
            "type": "openstack_networking_port_v2",
            "change": {"actions": ["create"], "progress": "queued"},
        },
    ],
}

CONFIG_DICT = {
    "cluster_name": "foo-123",
    "domain": "magic-castle.cloud",
    "image": "CentOS-7-x64-2021-11",
    "nb_users": 17,
    "instances": {
        "mgmt": {"type": "p4-6gb", "count": 1},
        "login": {"type": "p4-6gb", "count": 1},
        "node": {"type": "p2-3gb", "count": 3},
    },
    "volumes": {
        "nfs": {
            "home": {"size": 50},
            "project": {"size": 1},
            "scratch": {"size": 1},
        }
    },
    "public_keys": [""],
    "hieradata": 'profile::base::admin_email: "frederic.fortier-chouinard@calculquebec.ca"\n'
    "jupyterhub::enable_otp_auth: false",
    "guest_passwd": '1234\\56789\t "',
}

VALID_CLUSTER_CONFIGURATION = {
    "cloud": {"id": 1, "name": "test-project"},
    "cluster_name": "a-123-45",
    "nb_users": 10,
    "guest_passwd": "password-123",
    "volumes": {
        "nfs": {
            "home": {"size": 100},
            "scratch": {"size": 50},
            "project": {"size": 50},
        }
    },
    "instances": {
        "mgmt": {"type": "p4-6gb", "count": 1, "tags": ["mgmt", "puppet", "nfs"]},
        "login": {"type": "p4-6gb", "count": 1, "tags": ["login", "proxy", "public"]},
        "node": {"type": "p2-3gb", "count": 1, "tags": ["node"]},
    },
    "domain": "magic-castle.cloud",
    "public_keys": [""],
    "hieradata": "",
    "image": "CentOS-7-x64-2021-11",
}
