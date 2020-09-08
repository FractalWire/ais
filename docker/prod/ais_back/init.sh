#!/bin/sh
# Starting script for the aisreceiver service

# should be an environment variable
# SERVER_DB='db'
echo -n "Waiting for server $POSTGRES_HOST to start."
until ping -c 1 $POSTGRES_HOST > /dev/null 2>&1; do
    echo -n '.'
    sleep 1
done

echo
echo "The server $POSTGRES_HOST is online"

python manage.py waitdb \
 && echo \
 && python manage.py migrate  \
 && echo \
 && python manage.py "$@"
