# Developer Documentation

## Requirements

- Docker Engine 19.03.0+
- Docker Compose
- Bash interpreter

## Running the application in development mode

Clone this repository.
```shell script
git clone https://github.com/ComputeCanada/magic_castle-ui.git
```
Then, run the development Docker container. This documentation shows two ways of achieving this: with a regular setup or with VS Code.

> **Note:** When running this development container, three important bind mounts will be created:
> 1. A bind mount between the project's `app` directory and the container's `/home/mcu/app` directory to ensure that modifications in the backend code are applied instantly. However, the container cannot modify this directory, it is readonly.
> 2. A bind mount between the project root directory and the container's `/workspace` directory. This bind mount is necessary to modify the application code in the running container from the host system.
> 3. A bind mount between the project's `clusters_backup` directory and the container's `/home/mcu/clusters` directory to ensure that Terraform state files and logs are backed up.

#### Option 1 (regular setup)

1. Start the Docker container.
   ````
   docker-compose -f docker-compose.yml -f docker-compose.dev.yml build
   docker-compose up
   ````
2. Open your browser and navigate to `http://localhost:5000`.

#### Option 2 (VS Code setup)

1. Install the [Remote - Containers](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers) VS Code extension.

2. Start VS Code and run `Remote-Containers: Open Folder in Container` command from the Command Pallette (`F1`). Then, select the repository folder.

3. Open your browser and navigate to `http://localhost:5000`.

4. Install the [Python](https://marketplace.visualstudio.com/items?itemName=ms-python.python) extension in the Dev Container.

## Modifying the backend code

You can modify any file in the `/workspace/app` directory without a rebuild, because of the bind mount created previously.

## Modifying the frontend code

By default, modifications to the frontend code (in `/workspace/frontend`) do require a rebuild.

However, you can easily run a node development server inside the development container. First, you will need to explicitly specify the `VUE_APP_API_URL` environment variable, because the development server runs on a different port (8080) from the Flask server. Here is an example with the Flask server running on port 5000.
````shell script
cd /workspace/frontend
echo "VUE_APP_API_URL=http://localhost:5000/api" > .env.development.local
````
Then, you can start the Node development server.
````shell script
npm run serve
````
This will spawn a node server (most likely on `http://localhost:8080`) which will automatically reload the frontend code on any modification.

> To make the npm development server run faster, install and run npm on the host machine.

## Accessing clusters manually with Terraform

If there was a problem when modifying a cluster using the UI or you want to access the terraform logs, this section if for you.

#### Option 1 (recommended)

1. Start a shell within your running container.
2. Go to the directory of the target cluster.
   ```shell script
   cd ~/clusters/<CLUSTER NAME>.<DOMAIN>
   ```
3. Then, you can run any terraform command.

#### Option 2

Open the terminal on your host machine and access the `clusters_backup` directory.

1. Navigate to `<PROJECT DIR>/clusters_backup/<CLUSTER_NAME>.<DOMAIN>`.
2. Delete the folder named `.terraform`.
3. Download [magic_castle-openstack-7.3.zip
](https://github.com/ComputeCanada/magic_castle/releases/download/7.3/magic_castle-openstack-7.3.zip)
4. Extract the folder and copy the `openstack` folder in `<PROJECT DIR>/clusters_backup/<CLUSTER_NAME>.<DOMAIN>`.
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

