#!/bin/bash
# build the docker images

docker build -t ais_back -f docker/ais_back/Dockerfile.devel .

echo ''

docker build -t ais_front -f docker/ais_front/Dockerfile.devel .

echo ''

docker build -t ais_postgres -f docker/postgres/Dockerfile.devel .
