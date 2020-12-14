from os import path, environ

# Regular constants
INSTANCE_CATEGORIES = ["mgmt", "login", "node"]
STORAGE_SPACES = ["home", "project", "scratch"]
AUTO_ALLOCATED_IP_LABEL = "Automatic allocation"

# Magic Castle
MAGIC_CASTLE_MODULE_SOURCE = "git::https://github.com/ComputeCanada/magic_castle.git"
MAGIC_CASTLE_VERSION_TAG = "9.1"

# Paths and filenames
CLUSTERS_PATH = path.join(environ["HOME"], "clusters")
APP_PATH = path.join(environ["HOME"], "app")
DATABASE_PATH = path.join(environ["HOME"], "database", "database.db")
SCHEMA_MIGRATIONS_DIRECTORY = path.join(APP_PATH, "database", "migrations")
TERRAFORM_STATE_FILENAME = "terraform.tfstate"
CONFIGURATION_FILE_PATH = path.join(environ["HOME"], "configuration.json")
