#!/usr/bin/env bash

repository='magic_castle-ui'
tag='latest'

echo "Building $repository..."
docker build --quiet --tag "$repository:$tag" .

echo "Running $repository..."
docker run --publish 5000:5000 "$repository"
