from os import path, environ

# Regular constants
INSTANCE_CATEGORIES = ["mgmt", "login", "node"]
STORAGE_SPACES = ["home", "project", "scratch"]
AUTO_ALLOCATED_IP_LABEL = "Automatic allocation"

# Magic Castle
MAGIC_CASTLE_MODULE_SOURCE = "git::https://github.com/ComputeCanada/magic_castle.git"
MAGIC_CASTLE_PUPPET_CONFIGURATION_URL = (
    "https://github.com/ComputeCanada/puppet-magic_castle.git"
)
MAGIC_CASTLE_VERSION_TAG = "10.2"
TERRAFORM_REQUIRED_VERSION = ">= 0.14.2"

# Paths and filenames
CLUSTERS_PATH = environ.get("MCH_CLUSTERS_PATH", path.join(environ["HOME"], "clusters"))
APP_PATH = environ.get("MCH_APP_PATH", path.join(environ["HOME"], "app"))
DATABASE_PATH = environ.get("MCH_DATABASE_PATH", path.join(environ["HOME"], "database"))
SCHEMA_MIGRATIONS_DIRECTORY = path.join(APP_PATH, "database", "migrations")
CONFIGURATION_FILE_PATH = environ.get("MCH_CONFIGURATION_FILE_PATH", environ["HOME"])

CONFIGURATION_FILENAME = "configuration.json"
DATABASE_FILENAME = "database.db"
TERRAFORM_STATE_FILENAME = "terraform.tfstate"
