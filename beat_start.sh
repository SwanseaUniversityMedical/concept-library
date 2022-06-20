#!/bin/bash

cd /var/www/concept_lib_sites/v1 && virtualenv  cllvirenv_v1 && . cllvirenv_v1/bin/activate && cd /var/www/concept_lib_sites/v1/CodeListLibrary_project &&  celery -A cll beat -l INFO


