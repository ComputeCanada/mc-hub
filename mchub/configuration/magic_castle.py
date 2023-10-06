from os import environ, path

TERRAFORM_STATE_FILENAME = "terraform.tfstate"
MAIN_TERRAFORM_FILENAME = "main.tf.json"

# Regular constants
STORAGE_SPACES = ["home", "project", "scratch"]

MAGIC_CASTLE_PUPPET_CONFIGURATION_URL = (
    "https://github.com/ComputeCanada/puppet-magic_castle.git"
)
TERRAFORM_REQUIRED_VERSION = ">= 1.2.1"

MAGIC_CASTLE_VERSION = environ.get("MAGIC_CASTLE_VERSION", "12.6.7")
MAGIC_CASTLE_PATH = environ.get("MAGIC_CASTLE_PATH", "git")
if MAGIC_CASTLE_PATH == "git":
    MAGIC_CASTLE_SOURCE = {
        "openstack": f"git::https://github.com/ComputeCanada/magic_castle.git//openstack?ref={MAGIC_CASTLE_VERSION}",
        "dns": {
            "cloudflare": f"git::https://github.com/ComputeCanada/magic_castle.git//dns/cloudflare?ref={MAGIC_CASTLE_VERSION}",
            "gcloud": f"git::https://github.com/ComputeCanada/magic_castle.git//dns/gcloud?ref={MAGIC_CASTLE_VERSION}",
        },
    }
else:
    MAGIC_CASTLE_SOURCE = {
        "openstack": path.join(".", "openstack"),
        "dns": {
            "cloudflare": path.join(".", "dns", "cloudflare"),
            "gcloud": path.join(".", "dns", "gcloud"),
        },
    }

MAGIC_CASTLE_ACME_KEY_PEM = environ.get("MAGIC_CASTLE_ACME_KEY_PEM", "")
