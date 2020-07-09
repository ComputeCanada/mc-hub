from os import path, environ

CLUSTERS_PATH = path.join(environ["HOME"], "clusters")
INSTANCE_CATEGORIES = ["mgmt", "login", "node"]
STORAGE_SPACES = ["home", "project", "scratch"]
MAGIC_CASTLE_RELEASE_PATH = path.join(
    environ["HOME"], "magic_castle-openstack-" + environ["MAGIC_CASTLE_VERSION"]
)
TERRAFORM_STATE_FILENAME = "terraform.tfstate"

