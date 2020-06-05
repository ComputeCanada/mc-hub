# Magic Castle UI

[![Build Status](https://travis-ci.com/ComputeCanada/magic_castle-ui.svg?branch=master)](https://travis-ci.com/ComputeCanada/magic_castle-ui)

Web interface to launch Magic Castles without knowing anything about Terraform.

## Requirements

- Docker
- Bash interpreter

## Running the pre-built docker image

1. Source your project openrc file.
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
   docker run -d -p 5000:5000 --env-file ./env.list \
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

## Building and running from source

1. Clone this repository.
   ```
   git clone https://github.com/ComputeCanada/magic_castle-ui.git
   cd magic-castle-ui
   ```
2. Source your project openrc file.
   ```
   source _project_-openrc.sh
   ```
3. Create a directory named `clusters_backup` and give it the proper owner and group.
   ```
   mkdir clusters_backup
   sudo chown 1000:1000 clusters_backup
   ```
4. Run start.sh. This will build and run the docker container for the Flask Server.
   ```
   ./start.sh
   ```
   > **Note:** This will create a bind mount in the `clusters_backup` directory. For more information, see the
   > section on _Cluster storage & backup_.
   
5. Navigate to `http://localhost:5000` and start building clusters!

6. Kill the container when you are done.
   ```
   docker kill <CONTAINER ID>
   ```

## Running tests
Make sure you have built an image of Magic Castle UI first and that you have sourced the openrc file, 
as shown in the previous step.
Then, run the following command:
````shell script
docker run --env-file ./env.list "magic_castle-ui" python -m pytest
````

> **Check your existing clusters**: MC UI will overwrite the following cluster names when running tests: valid-1, missing-nodes, empty.

> **Note**: The tests require the existence of OpenStack's environment variables
> (achieved with `source _project_-openrc.sh`). However, no real API calls are made with these environment variables.

## Cluster storage & backup

Magic Castle clusters are built in the directory `/home/mcu/clusters/<cluster name>` inside the
docker container.
This folder contains the logs from terraform commands and the `terraform.tfstate` file.

By running the container according to the above instructions, a bind mount was created. This 
makes the `/home/mcu/clusters/<cluster name>` directory accessible to the host machine in
`<current directory>/clusters_backup`.
If one container is destroyed or fails, a new container will recover all the previously 
created clusters in the directory.

### Accessing clusters manually with Terraform

If there was a problem when destroying a cluster using the UI or you want to access the terraform logs,
this section if for you.

#### Option 1 (recommended)
Start a shell within your running container.
```shell script
docker ps  # Find the container id
docker exec -it <CONTAINER ID> /bin/sh

# Inside the container shell
cd ~/clusters/<CLUSTER NAME>
terraform show
```

#### Option 2
Open the terminal on your host machine and access the `clusters_backup` directory.
1. Navigate to `<PROJECT DIR>/clusters_backup/<CLUSTER_NAME>`.
2. Delete the folder named `.terraform`.
3. Download [magic_castle-openstack-7.2.zip
](https://github.com/ComputeCanada/magic_castle/releases/download/7.2/magic_castle-openstack-7.2.zip)
4. Extract the folder and copy the `openstack` folder in `<PROJECT DIR>/clusters_backup/<CLUSTER_NAME>`.
5. Edit the following line in main.tf:
   ```
   source = "/home/mcu/magic_castle-openstack-7.2/openstack"
   ```
   And change it for:
   ```
   source = "./openstack"
   ```
6. Open a terminal and run the following command:
   ````
   terraform init
   ````
7. Now, you should be able to modify the cluster on your host machine with terraform.
   ```
   terraform show
   ```
