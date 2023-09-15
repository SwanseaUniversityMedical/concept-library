#!/bin/bash

if [ ! -z $AWAIT_POSTGRES ] && [ $AWAIT_POSTGRES = "True" ]; then
  /bin/wait-for-it.sh -t 0 postgres:5432 -- echo "Postgres is live"
fi

cd /var/www/concept_lib_sites/v1/CodeListLibrary_project
celery -A cll worker -l INFO --purge
