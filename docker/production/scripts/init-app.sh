#!/usr/bin/env sh

echo "===================================="
echo "======= Starting application ======="
echo "===================================="

if [ ! -z $CLL_READ_ONLY ] && [ $CLL_READ_ONLY = 1 ]; then
  echo "===================================="
  echo "========== Migrating app ==========="
  echo "===================================="

  python /var/www/concept_lib_sites/v1/CodeListLibrary_project/manage.py migrate
  python /var/www/concept_lib_sites/v1/CodeListLibrary_project/manage.py makemigrations
fi

if [ ! -z $DEBUG ] && [ $DEBUG = 0 ]; then
  echo "===================================="
  echo "========== Compiling app ==========="
  echo "===================================="

  python /var/www/concept_lib_sites/v1/CodeListLibrary_project/manage.py compilescss
  python /var/www/concept_lib_sites/v1/CodeListLibrary_project/manage.py collectstatic --noinput --clear --ignore=*.scss
  python /var/www/concept_lib_sites/v1/CodeListLibrary_project/manage.py compress
  python /var/www/concept_lib_sites/v1/CodeListLibrary_project/manage.py collectstatic --noinput --ignore=*.scss
fi
