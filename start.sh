#!/usr/bin/env bash

# Stop on first non-zero return code
set -e

repository='magic_castle-ui'
tag='latest'
port=5000
host_clusters_path=$(pwd)/clusters_backup
host_app_path=$(pwd)/app
container_clusters_path='/home/mcu/clusters'
container_app_path='/home/mcu/app'

echo "Building $repository..."
if [[ $1 == '--verbose' ]]; then
  docker build --tag "$repository:$tag" .
else
  docker build --tag "$repository:$tag" --quiet .
fi

echo "Running $repository..."
container_id=$(docker run \
  --detach \
  --rm \
  --env-file ./env.list \
  --mount "type=bind,source=$host_clusters_path,target=$container_clusters_path" \
  --mount "type=bind,source=$host_app_path,target=$container_app_path,readonly" \
  --publish $port:$port \
  "$repository")

echo "Go to http://localhost:$port/"
echo "Don't forget to kill your container when you are done:"
echo "docker kill $container_id"
