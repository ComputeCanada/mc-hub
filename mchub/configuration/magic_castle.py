from os import environ, path

from .env import CLUSTERS_PATH

TERRAFORM_STATE_FILENAME = "terraform.tfstate"
MAIN_TERRAFORM_FILENAME = "main.tf.json"

# Regular constants
INSTANCE_CATEGORIES = ["mgmt", "login", "node"]
STORAGE_SPACES = ["home", "project", "scratch"]

MAGIC_CASTLE_PUPPET_CONFIGURATION_URL = (
    "https://github.com/ComputeCanada/puppet-magic_castle.git"
)
TERRAFORM_REQUIRED_VERSION = ">= 1.1.0"

MAGIC_CASTLE_VERSION = environ.get("MAGIC_CASTLE_VERSION", "11.9.0")
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
    # Terraform only accepts relative path from the current module
    # but it is easier to define it as an absolute path from a admin
    # perspective
    relative_path = path.relpath(MAGIC_CASTLE_PATH, path.join(CLUSTERS_PATH, 'cluster'))
    MAGIC_CASTLE_SOURCE = {
        "openstack" : path.join(relative_path, "openstack"),
        "dns" : {
            "cloudflare" : path.join(relative_path, "dns", "cloudflare"),
            "gcloud" : path.join(relative_path, "dns", "gcloud")
        }
    }

MAGIC_CASTLE_ACME_KEY_PEM = environ.get("MAGIC_CASTLE_ACME_KEY_PEM", "")
