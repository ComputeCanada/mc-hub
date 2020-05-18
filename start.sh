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
echo "Go to http://localhost:$port/"
docker run \
  --env-file ./env.list \
  --mount "type=volume,source=clusters,destination=$clusters_path" \
  --publish $port:$port \
  "$repository"
