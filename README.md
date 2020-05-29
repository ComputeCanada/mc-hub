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
2. Copy env.list from this repository to your current directory.
3. Run the [latest image](https://hub.docker.com/repository/docker/fredericfc/magic_castle-ui) of Magic Castle UI.
   ```shell script   
   docker run -d -p 5000:5000 --env-file ./env.list fredericfc/magic_castle-ui:latest
   ```
4.  Navigate to `http://localhost:5000` and start building clusters!
5. Kill the container when you are done.
   ```
   docker kill <CONTAINER ID>
   ```

## Building and running from source

1. Clone this repository.
   ```
   git clone https://github.com/ComputeCanada/magic_castle-ui.git
   ```

2. Source your project openrc file.
    ```
    source _project_-openrc.sh
    ```
3. Run start.sh. This will build and run the docker container for the Flask Server.
   ```
   cd magic-castle-ui
   ./start.sh
   ```
   
4. Navigate to `http://localhost:5000` and start building clusters!

5. Kill the container when you are done.
   ```
   docker kill <CONTAINER ID>
   ```

## Running Tests
Make sure you have built an image of Magic Castle UI first, as shown in the previous step. Then, run the following command:
````shell script
docker run --env-file ./env.list "magic_castle-ui" python -m pytest
````

> **Check your existing clusters**: MC UI will overwrite the following cluster names when running tests: valid-1, missing-nodes, empty.

## Cluster storage & backup

All Magic Castle clusters are built in a directory shared with the
host computer: `<PROJECT ROOT>/clusters_backup`. If one container is destroyed or
fails, a new container will recover all the previously created clusters in the
directory.

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
This option only works if you used the `--mount` option when running your docker instance. Open the terminal on your host machine and access the `clusters_backup` directory.
1. Navigate to `<PROJECT DIR>/clusters_backup/<CLUSTER_NAME>`.
2. Delete de folder named `.terraform`.
3. Download [magic_castle-openstack-7.2.zip
](https://github.com/ComputeCanada/magic_castle/releases/download/7.2/magic_castle-openstack-7.2.zip)
4. Extract the folder and copy the `openstack` folder in `<PROJECT DIR>/clusters_backup/<CLUSTER_NAME>`.
5. Edit the following line in main.tf:
   ```
   source = "/home/mcu/magic_castle-openstack-6.4/openstack"
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
