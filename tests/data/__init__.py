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
    "cloud": {"id": 1, "name": "project-alice"},
    "cluster_name": "valid1",
    "nb_users": 10,
    "guest_passwd": "password-123",
    "volumes": {
        "nfs": {
            "home": {"size": 100},
            "project": {"size": 50},
            "scratch": {"size": 50},
        }
    },
    "instances": {
        "mgmt": {"type": "p4-6gb", "count": 1, "tags": ["mgmt", "nfs", "puppet"]},
        "login": {"type": "p4-6gb", "count": 1, "tags": ["login", "proxy", "public"]},
        "node": {"type": "p2-3gb", "count": 1, "tags": ["node"]},
    },
    "domain": "calculquebec.cloud",
    "public_keys": ["ssh-rsa FAKE"],
    "image": "CentOS-7-x64-2021-11",
    "hieradata": "",
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
