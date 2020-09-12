#!/bin/bash
# Starting script for the aisreceiver service

source /init.d/init.db_online.sh
source /init.d/init.secrets_to_env.sh

wait_db
export_secrets

python manage.py waitdb \
 && echo \
 && python manage.py migrate  \
 && echo \
 && python manage.py "$@"

exit 0
