#!/bin/bash

start_worker=0;
if [ -z $DEBUG ] || [ $DEBUG = "False" ]; then
  start_worker=1;

  if [ -z $IS_DEVELOPMENT_PC ] || [ $IS_DEVELOPMENT_PC = "False" ]; then
    if [ ! -z $IS_DEMO ] && [ $IS_DEMO = "True" ]; then
      start_worker=0;
    elif [ ! -z $CLL_READ_ONLY ] && [ $CLL_READ_ONLY = "True" ]; then
      start_worker=0;
    elif [ ! -z $IS_INSIDE_GATEWAY ] && [ $IS_INSIDE_GATEWAY = "True" ]; then
      start_worker=0;
    fi
  fi
fi

if [ $start_worker -eq 1 ]; then
  # Await web app healthy
  printf '\n[CeleryBeat] Awaiting App healthy state .'
  until /bin/healthcheck.sh; do
    printf ' .'
    sleep 5
  done

  printf '\n[CeleryBeat] Completed!\n' + '\n[CeleryBeat] Application healthy, starting celery-beat...\n\n'

  # Workdir
  cd /var/www/concept_lib_sites/v1/CodeListLibrary_project

  # Run worker
  python -m celery -A cll beat -l INFO --max-interval 300
else
  exit 0
fi
