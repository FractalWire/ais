#!/bin/bash
# build the docker images

docker build -t ais -f docker/ais/Dockerfile.devel .

echo ''

docker build -t postgres-ais -f docker/postgres/Dockerfile.devel .
