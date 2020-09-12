#!/bin/bash
# Wait until DB is online

function wait_db {
    test -z "$POSTGRES_HOST" && exit 1

    echo -n "Waiting for server $POSTGRES_HOST to start."
    until netcat -z $POSTGRES_HOST 5432 > /dev/null 2>&1; do
        echo -n '.'
        sleep 1
    done

    echo
    echo "The server $POSTGRES_HOST is online"

    return 0
}
