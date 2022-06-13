DEFAULT = {
    "cloud": {"id": None, "name": None},
    "cluster_name": "",
    "domain": None,
    "image": None,
    "nb_users": 10,
    "instances": {
        "mgmt": {
            "type": None,
            "count": 1,
            "tags": ["mgmt", "nfs", "puppet"],
        },
        "login": {
            "type": None,
            "count": 1,
            "tags": ["login", "proxy", "public"],
        },
        "node": {
            "type": None,
            "count": 1,
            "tags": ["node"],
        },
    },
    "volumes": {
        "nfs": {
            "home": {"size": 100},
            "project": {"size": 100},
            "scratch": {"size": 100},
        },
    },
    "public_keys": [],
    "guest_passwd": "",
    "hieradata": "",
}
