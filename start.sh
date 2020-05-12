#!/usr/bin/env bash

# Stop on first non-zero return code
set -e

repository='magic_castle-ui'
tag='latest'

echo "Building $repository..."
docker build --tag "$repository:$tag" .

echo "Running $repository..."
docker run --env-file ./env.list --publish 5000:5000 "$repository"
