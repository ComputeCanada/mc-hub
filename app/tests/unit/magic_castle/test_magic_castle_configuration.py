from models.magic_castle.magic_castle_configuration import MagicCastleConfiguration
from tests.test_helpers import *  # noqa;
from exceptions.server_exception import ServerException
from tests.mocks.configuration.config_mock import config_auth_none_mock  # noqa;


def test_constructor_none():
    assert MagicCastleConfiguration().to_dict() == {}


def test_constructor_valid():
    CONFIG_DICT = {
        "cluster_name": "foo-123",
        "domain": "calculquebec.cloud",
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
    assert MagicCastleConfiguration(CONFIG_DICT).to_dict() == CONFIG_DICT


def test_constructor_empty_hieradata_valid():
    CONFIG_DICT = {
        "cluster_name": "foo-123",
        "domain": "calculquebec.cloud",
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
        "guest_passwd": '1234\\56789\t "',
        "hieradata": "",
    }
    assert MagicCastleConfiguration(CONFIG_DICT).to_dict() == CONFIG_DICT


def test_constructor_invalid_cluster_name():
    with pytest.raises(ServerException):
        MagicCastleConfiguration(
            {
                "cluster_name": "foo!",
                "domain": "calculquebec.cloud",
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
                "public_keys": [""],
                "hieradata": "",
                "guest_passwd": '1234\\56789\t "',
            }
        )


def test_get_from_dict_valid():
    CONFIG_DICT = {
        "cluster_name": "foo",
        "domain": "calculquebec.cloud",
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
        "public_keys": [""],
        "hieradata": 'profile::base::admin_email: "me@example.org"',
        "guest_passwd": '1234\\56789\t "',
    }
    assert MagicCastleConfiguration(CONFIG_DICT).to_dict() == CONFIG_DICT


def test_get_from_dict_empty_hieradata_valid():
    CONFIG_DICT = {
        "cluster_name": "foo",
        "domain": "calculquebec.cloud",
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
        "public_keys": [""],
        "hieradata": "",
        "guest_passwd": '1234\\56789\t "',
    }
    config = MagicCastleConfiguration(CONFIG_DICT)
    assert config.to_dict() == CONFIG_DICT


def test_get_from_main_file_valid():
    config = MagicCastleConfiguration.get_from_main_file(
        path.join(MOCK_CLUSTERS_PATH, "missingnodes.sub.example.com", "main.tf.json")
    )
    assert config.to_dict() == {
        "cluster_name": "missingnodes",
        "domain": "sub.example.com",
        "image": "CentOS-7-x64-2021-11",
        "nb_users": 10,
        "instances": {
            "mgmt": {"type": "p4-6gb", "count": 1, "tags": ["mgmt", "nfs", "puppet"]},
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
        "hieradata": "",
        "public_keys": ["ssh-rsa FAKE"],
        "guest_passwd": "password-123",
    }


def test_get_from_main_file_not_found():
    with pytest.raises(FileNotFoundError):
        MagicCastleConfiguration.get_from_main_file("empty")
    with pytest.raises(FileNotFoundError):
        MagicCastleConfiguration.get_from_main_file("non-existing")


def test_update_main_file():
    CONFIG_DICT = {
        "cluster_name": "missingnodes",
        "domain": "sub.example.com",
        "image": "CentOS-7-x64-2021-11",
        "nb_users": 30,
        "instances": {
            "mgmt": {"type": "", "count": 1, "tags": ["mgmt", "nfs", "puppet"]},
            "login": {"type": "", "count": 1, "tags": ["login", "proxy", "public"]},
            "node": {"type": "", "count": 12, "tags": ["node"]},
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
    }

    modified_config = MagicCastleConfiguration(CONFIG_DICT)
    path_ = path.join(
        MOCK_CLUSTERS_PATH, "missingnodes.sub.example.com", "main.tf.json"
    )
    modified_config.update_main_file(path_)
    saved_config = MagicCastleConfiguration.get_from_main_file(path_)
    assert saved_config.to_dict() == CONFIG_DICT


def test_properties():
    config = MagicCastleConfiguration(
        {
            "cluster_name": "foo",
            "domain": "calculquebec.cloud",
            "image": "CentOS-7-x64-2021-11",
            "nb_users": 17,
            "instances": {
                "mgmt": {"type": "", "count": 1, "tags": ["mgmt", "nfs", "puppet"]},
                "login": {"type": "", "count": 1, "tags": ["login", "proxy", "public"]},
                "node": {"type": "", "count": 3, "tags": ["node"]},
            },
            "volumes": {
                "nfs": {
                    "home": {"size": 50},
                    "project": {"size": 1},
                    "scratch": {"size": 1},
                }
            },
            "public_keys": ["ssh-rsa FAKE"],
            "guest_passwd": '1234\\56789\t "',
            "hieradata": "",
        }
    )
    assert config.cluster_name == "foo"
    assert config.domain == "calculquebec.cloud"
