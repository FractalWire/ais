#!/bin/bash
# build the docker images

ENV=$(test -z "$ENV" && echo "devel" || echo "$ENV")

case "$ENV" in
    "devel"|"prod") ;;
    *)
        echo "ENV variable must be 'devel' or 'prod'"
        exit 1
        ;;
esac

docker build -t "ais_back:$ENV" -f "docker/$ENV/ais_back/Dockerfile" .

echo ''

docker build -t "ais_front:$ENV" -f "docker/$ENV/ais_front/Dockerfile" .

echo ''

docker build -t "ais_postgres:$ENV" -f "docker/$ENV/postgres/Dockerfile" .

exit 0
