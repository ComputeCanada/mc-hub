from os import environ

TERRAFORM_STATE_FILENAME = "terraform.tfstate"
MAIN_TERRAFORM_FILENAME = "main.tf.json"

# Regular constants
STORAGE_SPACES = ["home", "project", "scratch"]

MAGIC_CASTLE_REPO_URL = "https://github.com/ComputeCanada/magic_castle"
MAGIC_CASTLE_PUPPET_CONFIGURATION_URL = (
    "https://github.com/ComputeCanada/puppet-magic_castle.git"
)
TERRAFORM_REQUIRED_VERSION = ">= 1.2.1"

MAGIC_CASTLE_VERSION = environ.get("MAGIC_CASTLE_VERSION", "11.9.6")
MAGIC_CASTLE_PATH = environ.get("MAGIC_CASTLE_PATH", "http")
MAGIC_CASTLE_SOURCE = {
    "aws": "",
    "azure": "",
    "gcp": "",
    "openstack": "",
    "ovh": "",
    "dns": {"cloudflare": "", "gcloud": ""},
}

if MAGIC_CASTLE_PATH == "http":
    source = f"{MAGIC_CASTLE_REPO_URL}/archive/refs/tags/{MAGIC_CASTLE_VERSION}.tar.gz"
    source = f"{source}//magic_castle-{MAGIC_CASTLE_VERSION}/{{provider}}"
elif MAGIC_CASTLE_PATH == "git":
    source = f"git::{MAGIC_CASTLE_REPO_URL}.git"
    source = f"{source}//{{provider}}?ref={MAGIC_CASTLE_VERSION}"
else:
    source = "."
    source = f"{source}/{{provider}}"

for provider in MAGIC_CASTLE_SOURCE:
    if not isinstance(MAGIC_CASTLE_SOURCE[provider], dict):
        MAGIC_CASTLE_SOURCE[provider] = source.format(provider=provider)
    else:
        submodule = provider
        for provider in MAGIC_CASTLE_SOURCE[submodule]:
            MAGIC_CASTLE_SOURCE[submodule][provider] = source.format(
                provider=f"{submodule}/{provider}"
            )

MAGIC_CASTLE_ACME_KEY_PEM = environ.get("MAGIC_CASTLE_ACME_KEY_PEM", "")
