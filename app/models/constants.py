from os import path, environ

CLUSTERS_PATH = path.join(environ["HOME"], "clusters")
INSTANCE_CATEGORIES = ["mgmt", "login", "node"]
STORAGE_SPACES = ["home", "project", "scratch"]
MAGIC_CASTLE_RELEASE_PATH = path.join(
    environ["HOME"], "magic_castle-openstack-" + environ["MAGIC_CASTLE_VERSION"]
)
APP_PATH = path.join(environ["HOME"], "app")
DATABASE_PATH = path.join(environ["HOME"], "database", "database.db")
SCHEMA_MIGRATIONS_DIRECTORY = path.join(APP_PATH, "database", "migrations")
TERRAFORM_STATE_FILENAME = "terraform.tfstate"
