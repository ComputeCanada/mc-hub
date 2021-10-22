from models.magic_castle.magic_castle_configuration import MagicCastleConfiguration
from tests.test_helpers import *  # noqa;
from exceptions.server_exception import ServerException
from tests.mocks.configuration.config_mock import config_auth_none_mock  # noqa;


def test_constructor_none():
    config = MagicCastleConfiguration()
    assert config.dump() == {}


def test_constructor_valid():
    config = MagicCastleConfiguration(
        {
            "cluster_name": "foo-123",
            "domain": "calculquebec.cloud",
            "image": "CentOS-7-x64-2020-11",
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
    )
    assert config.dump() == {
        "cluster_name": "foo-123",
        "domain": "calculquebec.cloud",
        "image": "CentOS-7-x64-2020-11",
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


def test_constructor_no_hieradata_valid():
    config = MagicCastleConfiguration(
        {
            "cluster_name": "foo-123",
            "domain": "calculquebec.cloud",
            "image": "CentOS-7-x64-2020-11",
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
            "guest_passwd": '1234\\56789\t "',
        }
    )
    assert config.dump() == {
        "cluster_name": "foo-123",
        "domain": "calculquebec.cloud",
        "image": "CentOS-7-x64-2020-11",
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
        "hieradata": "",
        "guest_passwd": '1234\\56789\t "',
    }


def test_constructor_invalid_cluster_name():
    with pytest.raises(ServerException):
        MagicCastleConfiguration(
            {
                "cluster_name": "foo!",
                "domain": "calculquebec.cloud",
                "image": "CentOS-7-x64-2020-11",
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
                "hieradata": "",
                "guest_passwd": '1234\\56789\t "',
            }
        )

    with pytest.raises(ServerException):
        MagicCastleConfiguration(
            {
                "cluster_name": "foo_underscore",
                "domain": "calculquebec.cloud",
                "image": "CentOS-7-x64-2020-11",
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
                "hieradata": "",
                "guest_passwd": '1234\\56789\t "',
            }
        )


def test_constructor_invalid_domain():
    with pytest.raises(ServerException):
        MagicCastleConfiguration(
            {
                "cluster_name": "foo",
                "domain": "invalid.cloud",
                "image": "CentOS-7-x64-2020-11",
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
                "hieradata": "",
                "guest_passwd": '1234\\56789\t "',
            }
        )


def test_get_from_dict_valid():
    config = MagicCastleConfiguration.get_from_dict(
        {
            "cluster_name": "foo",
            "domain": "calculquebec.cloud",
            "image": "CentOS-7-x64-2020-11",
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
            "hieradata": 'profile::base::admin_email: "me@example.org"',
            "guest_passwd": '1234\\56789\t "',
        }
    )
    assert config.dump() == {
        "cluster_name": "foo",
        "domain": "calculquebec.cloud",
        "image": "CentOS-7-x64-2020-11",
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
        "hieradata": 'profile::base::admin_email: "me@example.org"',
        "guest_passwd": '1234\\56789\t "',
    }


def test_get_from_dict_empty_hieradata_valid():
    config = MagicCastleConfiguration.get_from_dict(
        {
            "cluster_name": "foo",
            "domain": "calculquebec.cloud",
            "image": "CentOS-7-x64-2020-11",
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
            "hieradata": "",
            "guest_passwd": '1234\\56789\t "',
        }
    )
    assert config.dump() == {
        "cluster_name": "foo",
        "domain": "calculquebec.cloud",
        "image": "CentOS-7-x64-2020-11",
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
        "hieradata": "",
        "guest_passwd": '1234\\56789\t "',
    }


def test_get_from_main_tf_json_file_valid():
    config = MagicCastleConfiguration.get_from_main_tf_json_file(
        "missingnodes.sub.example.com"
    )
    assert config.dump() == {
        "cluster_name": "missingnodes",
        "domain": "sub.example.com",
        "image": "CentOS-7-x64-2020-11",
        "nb_users": 10,
        "instances": {
            "mgmt": {"type": "p4-6gb", "count": 1},
            "login": {"type": "p4-6gb", "count": 1},
            "node": {"type": "p2-3gb", "count": 1},
        },
        "volumes": {
            "nfs": {
                "home": {"size": 100},
                "project": {"size": 50},
                "scratch": {"size": 50},
            }
        },
        "hieradata": "",
        "guest_passwd": "password-123",
    }


def test_get_from_main_tf_json_file_not_found():
    with pytest.raises(FileNotFoundError):
        MagicCastleConfiguration.get_from_main_tf_json_file("empty")
    with pytest.raises(FileNotFoundError):
        MagicCastleConfiguration.get_from_main_tf_json_file("non-existing")


def test_get_from_state_file_missing_nodes():
    config = MagicCastleConfiguration.get_from_state_file(
        "missingnodes.sub.example.com"
    )
    assert config.dump() == {
        "cluster_name": "missingnodes",
        "domain": "sub.example.com",
        "image": "CentOS-7-x64-2020-11",
        "nb_users": 10,
        "instances": {
            "mgmt": {"type": "", "count": 0},
            "login": {"type": "", "count": 0},
            "node": {"type": "", "count": 0},
        },
        "storage": {
            "nfs": {
                "home": {"size": 100},
                "project": {"size": 50},
                "scratch": {"size": 50},
            }
        },
        "public_keys": ["ssh-rsa FAKE"],
        "hieradata": "",
        "guest_passwd": "password-123",
    }


def test_get_from_state_file_empty():
    config = MagicCastleConfiguration.get_from_state_file(
        "empty-state.calculquebec.cloud"
    )
    assert config.dump() == {
        "cluster_name": "empty-state",
        "domain": "calculquebec.cloud",
        "image": "",
        "nb_users": 0,
        "instances": {
            "mgmt": {"type": "", "count": 0},
            "login": {"type": "", "count": 0},
            "node": {"type": "", "count": 0},
        },
        "volumes": {
            "nfs": {
                "home": {"size": 0},
                "project": {"size": 0},
                "scratch": {"size": 0},
            }
        },
        "public_keys": [""],
        "hieradata": "",
        "guest_passwd": "",
    }


def test_get_from_state_file_not_found():
    with pytest.raises(FileNotFoundError):
        MagicCastleConfiguration.get_from_state_file("non-existing")


def test_update_main_tf_json_file():
    modified_config = MagicCastleConfiguration.get_from_dict(
        {
            "cluster_name": "missingnodes",
            "domain": "sub.example.com",
            "image": "CentOS-7-x64-2020-11",
            "nb_users": 30,
            "instances": {
                "mgmt": {"type": "p4-6gb", "count": 1},
                "login": {"type": "p4-6gb", "count": 1},
                "node": {"type": "p2-3gb", "count": 12},
            },
            "storage": {
                "type": "nfs",
                "home_size": 400,
                "project_size": 12,
                "scratch_size": 50,
            },
            "public_keys": ["ssh-rsa FOOBAR"],
            "hieradata": "",
            "guest_passwd": "",
            "os_floating_ips": [],
        }
    )
    modified_config.update_main_tf_json_file()
    saved_config = MagicCastleConfiguration.get_from_main_tf_json_file(
        "missingnodes.sub.example.com"
    )
    assert saved_config.dump() == {
        "cluster_name": "missingnodes",
        "domain": "sub.example.com",
        "image": "CentOS-7-x64-2020-11",
        "nb_users": 30,
        "instances": {
            "mgmt": {"type": "p4-6gb", "count": 1},
            "login": {"type": "p4-6gb", "count": 1},
            "node": {"type": "p2-3gb", "count": 12},
        },
        "volumes": {
            "nfs": {
                "home": {"size": 400},
                "project": {"size": 12},
                "scratch": {"size": 50},
            }
        },
        "public_keys": ["ssh-rsa FOOBAR"],
        "hieradata": "",
        "guest_passwd": "",
        "os_floating_ips": ["100.101.102.103"],
    }


def test_get_hostname():
    config = MagicCastleConfiguration(
        {
            "cluster_name": "foo",
            "domain": "calculquebec.cloud",
            "image": "CentOS-7-x64-2020-11",
            "nb_users": 17,
            "instances": {
                "mgmt": {"type": "p4-6gb", "count": 1},
                "login": {"type": "p4-6gb", "count": 1},
                "node": {"type": "p2-3gb", "count": 3},
            },
            "storage": {
                "nfs": {
                    "home": {"size": 50},
                    "project": {"size": 1},
                    "scratch": {"size": 1},
                }
            },
            "public_keys": [""],
            "guest_passwd": '1234\\56789\t "',
            "hieradata": "",
            "os_floating_ips": [],
        }
    )
    assert config.get_hostname() == "foo.calculquebec.cloud"
