#!/usr/bin/env sh

echo "===================================="
echo "======= Starting application ======="
echo "===================================="

cd /var/www/concept_lib_sites/v1/CodeListLibrary_project

if [ ! -z $CLL_READ_ONLY ] && [ $CLL_READ_ONLY = 1 ]; then
  echo "===================================="
  echo "========== Migrating app ==========="
  echo "===================================="

  python manage.py migrate
  python manage.py makemigrations
fi

if [ ! -z $DEBUG ] && [ $DEBUG = 0 ]; then
  echo "===================================="
  echo "========== Compiling app ==========="
  echo "===================================="

  python manage.py compilescss
  python manage.py collectstatic --noinput --clear --ignore=*.scss
  python manage.py compress
  python manage.py collectstatic --noinput --ignore=*.scss
fi
