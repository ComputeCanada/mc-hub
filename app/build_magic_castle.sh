#!/bin/sh

# Stop on first non-zero return code
set -e

terraform init -plugin-dir /root/.terraform.d/plugin-cache/linux_amd64 >> terraform_init.log
terraform apply -auto-approve >> terraform_apply.log
