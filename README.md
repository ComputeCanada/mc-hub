# Magic Castle UI

[![Build Status](https://travis-ci.com/ComputeCanada/magic_castle-ui.svg?branch=master)](https://travis-ci.com/ComputeCanada/magic_castle-ui)

Web interface to launch Magic Castles without knowing anything about Terraform.

![Magic Castle UI demo](./demo/demo.gif)

## Requirements

- Docker
- Bash interpreter

## Basic setup

Before running the Magic Castle UI Docker container, you need to setup a few things.

1. Download or create a `clouds.yaml` file with your OpenStack cloud credentials. The cloud entry you want to use needs to be named `openstack`.
2. Copy the `clouds.yaml` file in the current directory.
3. Create a directory named `clusters_backup` and give it the proper permissions.
   ```
   mkdir clusters_backup
   sudo chmod -R 777 clusters_backup
   ```

## Running the pre-built Docker image

1. Run the [latest image](https://hub.docker.com/repository/docker/fredericfc/magic_castle-ui) of Magic Castle UI. This command binds the port 5000 from the container's Flask server to the host's port 80. You may change port 80 to another port.
   ```shell script
   docker run --rm -p 80:5000 \
     --mount "type=volume,source=database,target=/home/mcu/database" \
     --mount "type=bind,source=$(pwd)/clusters_backup,target=/home/mcu/clusters" \
     --mount "type=bind,source=$(pwd)/clouds.yaml,target=/home/mcu/.config/openstack/clouds.yaml" \
     fredericfc/magic_castle-ui:latest
   ```
   > **Note:** This will create a bind mount in the `clusters_backup` directory. For more information, see the section on _Cluster storage & backup_.   

2. Navigate to `http://localhost:80` and start building clusters!
3. Kill the container when you are done.
   ```
   docker kill <CONTAINER ID>
   ```

## Building the image from source

This requires installing Docker Compose.

1. Clone this repository.
   ```shell script
   git clone https://github.com/ComputeCanada/magic_castle-ui.git
   ```

2. Build the Docker image.
   ```shell script
   docker-compose build
   ```

3. Run the container. This will run the container in production mode.
   ```shell script
   docker-compose up
   ```

## Cluster storage & backup

Magic Castle clusters are built in the directory `/home/mcu/clusters/<cluster name>.<domain>` inside the
docker container.
This folder contains the logs from terraform commands, the plans and the state file.

By running the container according to the above instructions, a bind mount was created. This 
makes the `/home/mcu/clusters/<cluster name>.<domain>` directory accessible to the host machine in
`$(pwd)/clusters_backup`.

Also, a volume named `database` was created and will persist the database even if the container fails or is destroyed. However, the `database` volume can only be accessed from within a running container, not by the host machine.

In the end, if one Magic Castle UI container is destroyed or fails, a new container will recover all the previously 
created clusters in the directory.

## Debugging, contributing and advanced usage

Refer to the [Developer Documentation](./docs/developers.md).

## Adding SAML Authentication and HTTPS to Magic Castle UI

Check out the [wiki page](https://github.com/ComputeCanada/magic_castle-ui/wiki/Adding-SAML-Authentication-and-HTTPS-to-Magic-Castle-UI).
