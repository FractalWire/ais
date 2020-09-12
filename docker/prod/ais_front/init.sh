#!/bin/bash
# Starting script for the ais front web site

source /init.d/init.db_online.sh
source /init.d/init.secrets_to_env.sh

wait_db
export_secrets

cd /app

echo

# no mix here, we need a custom command
bin/ais_front eval "AisFront.Release.migrate"

echo
echo 'Launching the website now...'

bin/ais_front start

exit 0
