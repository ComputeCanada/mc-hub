#!/usr/bin/env bash

# Stop on first non-zero return code
set -e

repository='magic_castle-ui'
tag='latest'
port=5000
clusters_path='/home/mcu/clusters'

echo "Building $repository..."
if [[ $1 == '--verbose' ]]; then
  docker build --tag "$repository:$tag" .
else
  docker build --tag "$repository:$tag" --quiet .
fi

echo "Running $repository..."
container_id=$(docker run \
  --detach \
  --env-file ./env.list \
  --mount "type=volume,source=clusters,destination=$clusters_path" \
  --publish $port:$port \
  "$repository")

# Make mcu the owner of the clusters volume, instead of root
docker exec -it -u root "$container_id" /usr/bin/env chown mcu "$clusters_path"

echo "Go to http://localhost:$port/"
echo "Don't forget to kill your container when you are done:"
echo "docker kill $container_id"
