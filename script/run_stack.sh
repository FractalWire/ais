#!/bin/bash
# run the docker stack

ENV=[[ -z "$ENV" ]] && "devel" || "$ENV"

case "$ENV" in
    "devel"|"prod") ;;
    *)
        echo "ENV variable must be 'devel' or 'prod'"
        exit 1
        ;;
esac

docker stack deploy -c "docker/$ENV/stack.yml" ais

exit 0
