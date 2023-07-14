#!/bin/bash
cd /var/www/concept_lib_sites/v1/CodeListLibrary_project
celery -A cll beat -l INFO --max-interval 300
