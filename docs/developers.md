# Developer Documentation

In order to contribute or modify the code of Magic Castle UI, it is highly recommended to use Visual Studio Code, as it allows debugging and running tests easily inside the container environment. The _developer documentation_ will assume you are using Visual Studio Code.

## Requirements

- Docker Engine 19.03.0+
- Docker Compose
- Bash interpreter
- Visual Studio Code

## Initial setup

1. Clone this repository.
   ```
   git clone https://github.com/ComputeCanada/magic_castle-ui.git
   cd magic-castle-ui
   ```
2. Source your project openrc file. This will initialize the environment variables required to connect to the OpenStack API.
   ```
   source _project_-openrc.sh
   ```
3. Write the OpenStack environment variables to `openstack.env`, at the root of the project.
   ```
   printenv | grep OS_ > openstack.env
   ```
4. Create a directory named `clusters_backup` and give it the proper owner and group.
   ```
   mkdir clusters_backup
   sudo chown 1000:1000 clusters_backup
   ```

## Running and debugging the backend code

This is only available on Visual Studio Code right now.

1. Install the [Remote Development extension pack](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.vscode-remote-extensionpack).

2. Start VS Code and run `Remote-Containers: Open Folder in Container` command from the Command Pallette (`F1`).

   This will perform the following commands for you :
   ```
   docker-compose build
   docker-compose up
   ```

   > **Note:** When running this command, three bind mounts will be created:
   > 1. A bind mount between the project's `app` directory and the container's `/home/mcu/app` directory to ensure that modifications in the backend code are applied instantly. However, the container cannot modify this directory, it is readonly.
   > 2. A bind mount between the project's `clusters_backup` directory and the container's `/home/mcu/clusters` directory to ensure that Terraform state files and logs are backed up.
   > 3. A bind mount between the project root directory and the container's `/workspace` directory. This bind mount is necessary to have remote workspaces in VS Code.

3. Install the [Python](https://marketplace.visualstudio.com/items?itemName=ms-python.python) extension in the Dev Container.

4. Go to the `Run` icon in the left pane of VS Code and run the Python Attach launch configuration.
   
   This will attach a debugging to the Flask server and make it reachable on `localhost:5000`.

   At this point, you can add your own breakpoints in the backend code and run tests.

## Modifying the backend code

You can modify any file in the `app` directory
without a rebuild, because of the bind mount created previously.

## Modifying the frontend code

By default, modifications to the frontend code do require a rebuild.

However, you can easily run a node development server inside the development container:
````shell script
cd /workspace/frontend
npm run serve
````
This will spawn a node server (most likely on `http://localhost:8080`) which will automatically reload the frontend code
on any modification.

> Please note that changes take around a minute right now to be applied in the node development server.


## Accessing clusters manually with Terraform

If there was a problem when destroying a cluster using the UI or you want to access the terraform logs,
this section if for you.

#### Option 1 (recommended)
Start a shell within your running container.
```shell script
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

