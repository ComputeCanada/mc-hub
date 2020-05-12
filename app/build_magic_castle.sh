#!/bin/sh

/usr/local/bin/terraform init -plugin-dir /root/.terraform.d/plugin-cache/linux_amd64 >> terraform_init.log
/usr/local/bin/terraform apply -auto-approve >> terraform_apply.log