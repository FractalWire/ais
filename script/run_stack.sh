#!/bin/bash
# run the docker stack

export ENV=$(test -z "$ENV" && echo "devel" || echo "$ENV")

# set secrets if needed
script/set_secrets.sh

case "$ENV" in
    "devel"|"prod") ;;
    *)
        echo "ENV variable must be 'devel' or 'prod'"
        exit 1
        ;;
esac

docker stack deploy -c "docker/$ENV/stack.yml" ais

exit 0
