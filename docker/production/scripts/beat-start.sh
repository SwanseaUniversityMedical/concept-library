#!/bin/bash

if [ ! -z $IS_DEVELOPMENT_PC ] && [ $IS_DEVELOPMENT_PC = "True" ]; then
  /bin/wait-for-it.sh -t 0 postgres:5432 -- echo "Postgres is live"
fi

cd /var/www/concept_lib_sites/v1/CodeListLibrary_project
celery -A cll beat -l INFO --max-interval 300
