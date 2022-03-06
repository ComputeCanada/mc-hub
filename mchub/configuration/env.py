from os import path, environ, getcwd

from openstack.config.loader import OpenStackConfig

ALL_CLOUD_ID = [cloud.name for cloud in OpenStackConfig().get_all_clouds()]

# Regular constants
INSTANCE_CATEGORIES = ["mgmt", "login", "node"]
STORAGE_SPACES = ["home", "project", "scratch"]

MAGIC_CASTLE_PUPPET_CONFIGURATION_URL = (
    "https://github.com/ComputeCanada/puppet-magic_castle.git"
)
TERRAFORM_REQUIRED_VERSION = ">= 1.1.0"

# Paths and filenames
DEFAULT_CLOUD = environ.get("OS_CLOUD", ALL_CLOUD_ID[0])
RUN_PATH = environ.get("MCH_RUN_PATH", getcwd())
CLUSTERS_PATH = environ.get("MCH_CLUSTERS_PATH", path.join(RUN_PATH, "clusters"))
APP_PATH = environ.get("MCH_APP_PATH", path.join(RUN_PATH, "mchub"))
DIST_PATH = environ.get("MCH_DIST_PATH", path.join(RUN_PATH, "dist"))
DATABASE_PATH = environ.get("MCH_DATABASE_PATH", path.join(RUN_PATH, "database"))
SCHEMA_MIGRATIONS_DIRECTORY = path.join(APP_PATH, "database", "migrations")
CONFIGURATION_FILE_PATH = environ.get("MCH_CONFIGURATION_FILE_PATH", RUN_PATH)

# Magic Castle
MAGIC_CASTLE_VERSION = environ.get("MAGIC_CASTLE_VERSION", "11.8")
MAGIC_CASTLE_PATH = environ.get("MAGIC_CASTLE_PATH", "git")
if MAGIC_CASTLE_PATH == "git":
    MAGIC_CASTLE_SOURCE = {
        "openstack" : f"git::https://github.com/ComputeCanada/magic_castle.git//openstack?ref={MAGIC_CASTLE_VERSION}",
        "dns": {
            "cloudflare" : f"git::https://github.com/ComputeCanada/magic_castle.git//dns/cloudflare?ref={MAGIC_CASTLE_VERSION}",
            "gcloud" : f"git::https://github.com/ComputeCanada/magic_castle.git//dns/gcloud?ref={MAGIC_CASTLE_VERSION}"
        }
    }
else:
    MAGIC_CASTLE_SOURCE = {
        "openstack" : path.join(MAGIC_CASTLE_PATH, "openstack"),
        "dns" : {
            "cloudflare" : path.join(MAGIC_CASTLE_PATH, "dns", "cloudflare"),
            "gcloud" : path.join(MAGIC_CASTLE_PATH, "dns", "gcloud")
        }
    }

CONFIGURATION_FILENAME = "configuration.json"
DATABASE_FILENAME = "database.db"
TERRAFORM_STATE_FILENAME = "terraform.tfstate"

MAIN_TERRAFORM_FILENAME = "main.tf.json"
