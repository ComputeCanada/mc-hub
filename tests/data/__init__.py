from mchub.models.magic_castle.plan_type import PlanType

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

PLAN_TYPE = {
    "buildplanning.calculquebec.cloud": PlanType.BUILD,
    "created.calculquebec.cloud": PlanType.BUILD,
    "valid1.calculquebec.cloud": PlanType.DESTROY,
    "empty-state.calculquebec.cloud": None,
    "missingfloatingips.c3.ca": None,
    "missingnodes.c3.ca": None,
    "noowner.calculquebec.cloud": None,
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
