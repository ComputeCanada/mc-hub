from os import path, environ

# Regular constants
INSTANCE_CATEGORIES = ["mgmt", "login", "node"]
STORAGE_SPACES = ["home", "project", "scratch"]
AUTO_ALLOCATED_IP_LABEL = "Automatic allocation"

# Paths and filenames
MAGIC_CASTLE_RELEASE_PATH = path.join(
    environ["HOME"], "magic_castle-openstack-" + environ["MAGIC_CASTLE_VERSION"]
)
CLUSTERS_PATH = path.join(environ["HOME"], "clusters")
APP_PATH = path.join(environ["HOME"], "app")
DATABASE_PATH = path.join(environ["HOME"], "database", "database.db")
SCHEMA_MIGRATIONS_DIRECTORY = path.join(APP_PATH, "database", "migrations")
TERRAFORM_STATE_FILENAME = "terraform.tfstate"
CONFIGURATION_FILE_PATH = path.join(environ["HOME"], "configuration.json")
