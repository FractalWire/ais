#!/bin/bash
# Fetch and tag docker image from latest fractalwire build

ENV=$(test -z "$ENV" && echo "devel" || echo "$ENV")

case "$ENV" in
    "devel"|"prod") ;;
    *)
        echo "ENV variable must be 'devel' or 'prod'"
        exit 1
        ;;
esac

docker pull "fractalwire/ais_front:$ENV"
docker pull "fractalwire/ais_back:$ENV"
docker pull "fractalwire/ais_postgres:$ENV"

docker tag "fractalwire/ais_front:$ENV" "ais_front:$ENV"
docker tag "fractalwire/ais_back:$ENV" "ais_back:$ENV"
docker tag "fractalwire/ais_postgres:$ENV" "ais_postgres:$ENV"

exit 0
