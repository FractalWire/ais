#!/bin/sh
# Starting script for the ais front web site

echo -n "Waiting for server $POSTGRES_HOST to start."
until netcat -z $POSTGRES_HOST 5432 > /dev/null 2>&1; do
    echo -n '.'
    sleep 1
done

echo
echo "The server $POSTGRES_HOST is online"

cd /app

echo

# no mix here, we need a custom command
bin/ais_front eval "AisFront.Release.migrate"

echo
echo 'Launching the website now...'

bin/ais_front start
