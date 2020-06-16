# Developer Documentation

## Requirements

- Docker
- Bash interpreter

## Steps to build and run the Docker container from source

1. Clone this repository.
   ```
   git clone https://github.com/ComputeCanada/magic_castle-ui.git
   cd magic-castle-ui
   ```
2. Source your project openrc file. This will initialize the environment variables required to connect to the OpenStack API.
   ```
   source _project_-openrc.sh
   ```
3. Create a directory named `clusters_backup` and give it the proper owner and group.
   ```
   mkdir clusters_backup
   sudo chown 1000:1000 clusters_backup
   ```
4. Build the docker image.
   ```
   docker build --tag "magic_castle-ui:latest" .
   ```
5. Run the docker image. This will start the web server and expose it on ``localhost:5000``.
   ```shell script
   docker run \
      --rm \
      --env-file ./env.list \
      --mount "type=bind,source=$(pwd)/clusters_backup,target=/home/mcu/clusters" \
      --mount "type=bind,source=$(pwd)/app,target=/home/mcu/app,readonly" \
      --publish 5000:5000 \
      "magic_castle-ui"
   ```
   > **Note:** When running this command, two bind mounts will be created:
   > 1. A bind mount between the project's `app` directory and the container's `/home/mcu/app` directory
   to ensure that modifications in the backend code are applied instantly. However, the container
   > cannot modify this directory, it is readonly.
   > 2. A bind mount between the project's `clusters_backup` directory and
   > the container's `/home/mcu/clusters` directory to ensure that Terraform state files
   > and logs are backed up.
   
6. Navigate to `http://localhost:5000` to verify that the server is running and accessible locally.

7. Kill the container when you are done.
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

> **Note**: The tests require the existence of OpenStack's environment variables
> (achieved with `source _project_-openrc.sh`). However, no real API calls are made with these environment variables.

## Debugging the backend code

In order to setup debugging, the easiest way is to:

1. Setup your IDE to use the Python interpreter from the ``magic_castle-ui:latest`` Docker image.

2. Add the installation path of the python libraries to the interpreter configuration.
The libraries specific to Magic Castle UI are installed in `/home/mcu/.local/lib/python3.8/site-packages`.

3. Create a path mapping between the project's `app` directory and `/home/mcu/app`.

4. Create a run configuration for `app/server.py` using the Python interpreter configured previously.
Then, make sure the following additional arguments are included in the docker run command:
   ````shell script
   --entrypoint= \
   --rm \
   --env-file ./env.list \
   --mount "type=bind,source=$(pwd)/clusters_backup,target=/home/mcu/clusters" \
   --mount "type=bind,source=$(pwd)/app,target=/home/mcu/app,readonly" \
   --publish 5000:5000
   ```` 

5. Add the environment variables required by OpenStack to your run configuration. These can be found with:
    ````shell script
    printenv | grep "OS_"
    ````
6. Add breakpoints and start debugging with this run configuration.

The same steps can be applied to debugging the unit and integration tests.
Note that you need to use a pytest run configuration to debug the tests.

## Modifying the backend code

You can modify any file in the `app` directory
without a rebuild, because of the bind mount created previously.

If the changes are still not applied, kill the container and run it again:
````shell script
docker kill <CONTAINER ID>
docker run \
  --rm \
  --env-file ./env.list \
  --mount "type=bind,source=$(pwd)/clusters_backup,target=/home/mcu/clusters" \
  --mount "type=bind,source=$(pwd)/app,target=/home/mcu/app,readonly" \
  --publish 5000:5000 \
  "magic_castle-ui"
````

## Modifying the frontend code

By default, modifications to the frontend code do require a rebuild.

However, you can easily run a node development server:
````shell script
cd frontend
npm install
npm run serve
````
This will spawn a node server (most likely on `http://localhost:8080`) which will automatically reload the frontend code
on any modification.


## Accessing clusters manually with Terraform

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
3. Download [magic_castle-openstack-7.3.zip
](https://github.com/ComputeCanada/magic_castle/releases/download/7.3/magic_castle-openstack-7.3.zip)
4. Extract the folder and copy the `openstack` folder in `<PROJECT DIR>/clusters_backup/<CLUSTER_NAME>`.
5. Edit the following line in main.tf:
   ```
   source = "/home/mcu/magic_castle-openstack-7.3/openstack"
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

