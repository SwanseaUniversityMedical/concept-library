#!/bin/bash

# Await postgres healthcheck
if [ ! -z $AWAIT_POSTGRES ] && [ $AWAIT_POSTGRES = "True" ]; then
  /bin/wait-for-it.sh -t 0 postgres:5432 -- echo "Postgres is live"
fi

# Workdir
cd /var/www/concept_lib_sites/v1/CodeListLibrary_project

# Run worker
python -m celery -A cll beat -l INFO --max-interval 300
