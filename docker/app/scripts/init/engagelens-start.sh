#!/bin/bash

if [ ! -z $ENGAGELENS_START ] && [ $ENGAGELENS_START = "True" ]; then
  # Await web app healthy
  printf '\n[Engagelens] Awaiting App healthy state .'
  until /home/config_cll/health/web-healthcheck.sh; do
    printf ' .'
    sleep 5
  done

  printf '\n[Engagelens] Application healthy, starting engagelens...\n\n'

  # Workdir
  cd /var/www/concept_lib_sites/v1/engagelens

  # Run worker
  gunicorn -b 0.0.0.0:${ENGAGELENS_PORT:-8050} app:server --workers 2
else
  exit 0
fi
