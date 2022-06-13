# MC Hub

[![Build Status](https://travis-ci.com/ComputeCanada/mc-hub.svg?branch=master)](https://travis-ci.com/ComputeCanada/mc-hub)

Web interface to launch Magic Castle clusters without knowing anything about Terraform.

![MC Hub demo](./demo/demo.gif)

## Requirements

- Docker
- Bash interpreter

## Basic setup

Before running the MC Hub Docker container, you need to setup a few things.

1. Create a directory named `clusters_backup` and give it the proper permissions.
   ```
   mkdir clusters_backup
   sudo chmod -R 777 clusters_backup
   ```

If you are using Google Cloud as a DNS provider, do the following steps.

1. Create a service account that has permissions to manage the DNS settings (if you don't already have one). The account should have the _DNS Administrator_ role.
2. Create a new keypair and download it, in JSON format.
3. Copy the JSON key file to the root of the repository in a file named `gcloud-key.json`.
   ```
   cp <JSON key file location> gcloud-key.json
   ```

## Configuration

You need to create a configuration file named `configuration.json` in the current directory.

Read the section on the [JSON Configuration](./docs/configuration.md) for more information.

## Running the pre-built Docker image

1. Run the [latest image](https://hub.docker.com/repository/docker/cmdntrf/mc-hub) of MC Hub. This command binds the port 5000 from the container's Flask server to the host's port 8080. You may change port 8080 to another port. Also change `v9.1.2` for the latest version of MC Hub in the following command.

   If you are not using the Google Cloud DNS provider, remove the line `--mount "type=bind,source=$(pwd)/gcloud-key.json,target=/home/mcu/credentials/gcloud-key.json" \`.

   ```shell script
   docker run --rm -p 8080:5000 \
     --mount "type=volume,source=database,target=/home/mcu/database" \
     --mount "type=bind,source=$(pwd)/gcloud-key.json,target=/home/mcu/credentials/gcloud-key.json" \
     --mount "type=bind,source=$(pwd)/clusters_backup,target=/home/mcu/clusters" \
     --mount "type=bind,source=$(pwd)/configuration.json,target=/home/mcu/configuration.json" \
     cmdntrf/mc-hb:v9.1.2
   ```

2. Navigate to `http://localhost:8080` and start building clusters!
3. Kill the container when you are done.
   ```
   docker kill <CONTAINER ID>
   ```

## Building the image from source

Refer to the [Developer Documentation](./docs/developers.md).

## Cluster storage & backup

Magic Castle clusters are built in the directory `/home/mcu/clusters/<cluster name>.<domain>` inside the
docker container.
This folder contains the logs from terraform commands, the plans and the state file.

By running the container according to the above instructions, a bind mount was created. This
makes the `/home/mcu/clusters/<cluster name>.<domain>` directory accessible to the host machine in
`$(pwd)/clusters_backup`.

Also, a volume named `database` was created and will persist the database even if the container fails or is destroyed. However, the `database` volume can only be accessed from within a running container, not by the host machine.

In the end, if one MC Hub container is destroyed or fails, a new container will recover all the previously
created clusters in the directory.

## Adding SAML Authentication and HTTPS to MC Hub

### Option 1. Deploying with an Ansible playbook (recommended)

Use [Ansible MC Hub](https://github.com/ComputeCanada/ansible-mc-hub).

### Option 2. Configuring the server manually

Check out the [wiki page](https://github.com/ComputeCanada/mc-hub/wiki/Adding-SAML-Authentication-and-HTTPS-to-Magic-Castle-UI).
