# Magic Castle UI
Web interface to launch Magic Castles without knowing anything about Terraform.

## Requirements

- Docker
- Bash interpreter

## Setup for OpenStack Cloud

1. Source your project openrc file.
    ```
    source _project_-openrc.sh
    ```
2. Run start.sh. This will build and run the docker container for the Flask Server.
   ```
   ./start.sh
   ```
3. Navigate to `http://localhost:5000` and start building clusters!

4. Kill the container when you are done.
   ```
   docker kill <CONTAINER ID>
   ```


## Cluster storage & backup

All Magic Castle clusters are built in a directory shared with the
host computer: `<PROJECT ROOT>/clusters_backup`. If one container is destroyed or
fails, a new container will recover all the previously created clusters in the
directory.

### Accessing clusters manually with Terraform

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
2. Delete de folder named `.terraform`.
3. Download [magic_castle-openstack-6.4.zip
](https://github.com/ComputeCanada/magic_castle/releases/download/6.4/magic_castle-openstack-6.4.zip)
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

## Compute Canada Web Deployment Architecture

The app will eventually be accessible with a Compute Canada account to launch a Magic Castle cluster in shared project in Compute Canada cloud. Here is an early draft of the app design:

![Magic Castle CC UI Architecture](https://docs.google.com/drawings/d/e/2PACX-1vRe4JZSPiKY7tW5xO3WpsWoA8h0XC6zAjiMBwbgn-UIY6PMBC_5X-gJj9AbmdRCoEU4OXORh04xexO5/pub?w=721&amp;h=498 "Magic Castle CC UI Architecture")
