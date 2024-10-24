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
  printf '\n[CeleryWorker] Awaiting App healthy state .'
  until /bin/healthcheck.sh; do
    printf ' .'
    sleep 5
  done

  printf '\n[CeleryWorker] Completed!\n' + '\n[CeleryWorker] Application healthy, starting celery-worker...\n\n'

  # Workdir
  cd /var/www/concept_lib_sites/v1/CodeListLibrary_project

  # Run worker
  python -m celery -A cll worker -l INFO --purge
else
  exit 0
fi
