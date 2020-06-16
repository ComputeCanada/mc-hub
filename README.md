# Magic Castle UI

[![Build Status](https://travis-ci.com/ComputeCanada/magic_castle-ui.svg?branch=master)](https://travis-ci.com/ComputeCanada/magic_castle-ui)

Web interface to launch Magic Castles without knowing anything about Terraform.

## Requirements

- Docker
- Bash interpreter

## Running the pre-built docker image

1. Source your project openrc file. This will initialize the environment variables required to connect to the OpenStack API.
    ```
    source _project_-openrc.sh
    ```
2. Copy [env.list](https://github.com/ComputeCanada/magic_castle-ui/blob/master/env.list) from this repository to your current directory.
3. Create a directory named `clusters_backup` and give it the proper owner and group.
   ```
   mkdir clusters_backup
   sudo chown 1000:1000 clusters_backup
   ```
4. Run the [latest image](https://hub.docker.com/repository/docker/fredericfc/magic_castle-ui) of Magic Castle UI.
   ```shell script
   docker run --rm -p 5000:5000 --env-file ./env.list \
     --mount "type=bind,source=$(pwd)/clusters_backup,target=/home/mcu/clusters" \
     fredericfc/magic_castle-ui:latest
   ```
   > **Note:** This will create a bind mount in the `clusters_backup` directory. For more information, see
   > the section on _Cluster storage & backup_.

5. Navigate to `http://localhost:5000` and start building clusters!
6. Kill the container when you are done.
   ```
   docker kill <CONTAINER ID>
   ```

## Cluster storage & backup

Magic Castle clusters are built in the directory `/home/mcu/clusters/<cluster name>` inside the
docker container.
This folder contains the logs from terraform commands and the `terraform.tfstate` file.

By running the container according to the above instructions, a bind mount was created. This 
makes the `/home/mcu/clusters/<cluster name>` directory accessible to the host machine in
`$(pwd)/clusters_backup`.
If one container is destroyed or fails, a new container will recover all the previously 
created clusters in the directory.

## Developer documentation and advanced usage

Refer to the [Developer Documentation](./docs/developers.md).
