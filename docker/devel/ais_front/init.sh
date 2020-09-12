#!/bin/bash
# Starting script for the ais front web site

source /init.d/init.db_online.sh
source /init.d/init.secrets_to_env.sh

wait_db
export_secrets

cd /app

echo ''

mix do deps.get, ecto.setup

echo

cd /app/assets

npm install \
    && node node_modules/webpack/bin/webpack.js --mode development

echo
echo 'Launching the website now...'

cd /app

mix phx.server

exit 0
