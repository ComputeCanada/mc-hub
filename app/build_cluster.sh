#!/bin/sh

# Stop on first non-zero return code
set -e

terraform init -no-color -plugin-dir /root/.terraform.d/plugin-cache/linux_amd64 > terraform_init.log 2>&1
terraform apply -no-color -auto-approve > terraform_apply.log 2>&1
