from os import path, environ, getcwd

# Regular constants
INSTANCE_CATEGORIES = ["mgmt", "login", "node"]
STORAGE_SPACES = ["home", "project", "scratch"]

# Magic Castle
MAGIC_CASTLE_MODULE_SOURCE = "git::https://github.com/ComputeCanada/magic_castle.git"
MAGIC_CASTLE_PUPPET_CONFIGURATION_URL = (
    "https://github.com/ComputeCanada/puppet-magic_castle.git"
)
MAGIC_CASTLE_VERSION_TAG = "11.8"
TERRAFORM_REQUIRED_VERSION = ">= 1.1.0"

# Paths and filenames
DEFAULT_CLOUD = environ.get("OS_CLOUD", "openstack")
RUN_PATH = environ.get("MCH_RUN_PATH", getcwd())
CLUSTERS_PATH = environ.get("MCH_CLUSTERS_PATH", path.join(RUN_PATH, "clusters"))
APP_PATH = environ.get("MCH_APP_PATH", path.join(RUN_PATH, "mchub"))
DIST_PATH = environ.get("MCH_DIST_PATH", path.join(RUN_PATH, "dist"))
DATABASE_PATH = environ.get("MCH_DATABASE_PATH", path.join(RUN_PATH, "database"))
SCHEMA_MIGRATIONS_DIRECTORY = path.join(APP_PATH, "database", "migrations")
CONFIGURATION_FILE_PATH = environ.get("MCH_CONFIGURATION_FILE_PATH", RUN_PATH)

CONFIGURATION_FILENAME = "configuration.json"
DATABASE_FILENAME = "database.db"
TERRAFORM_STATE_FILENAME = "terraform.tfstate"

MAIN_TERRAFORM_FILENAME = "main.tf.json"
