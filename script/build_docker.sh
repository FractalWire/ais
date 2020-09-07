#!/bin/bash
# build the docker images

docker build -t ais_back -f docker/ais_back/Dockerfile.devel .

echo ''

docker build -t postgres-ais -f docker/postgres/Dockerfile.devel .
