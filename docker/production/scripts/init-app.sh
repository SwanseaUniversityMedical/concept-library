#!/bin/bash

cd /var/www/concept_lib_sites/v1/CodeListLibrary_project

if [ ! -z $AWAIT_POSTGRES ] && [ $AWAIT_POSTGRES = "True" ]; then
  echo "==========================================="
  echo "========== Waiting for Postgres ==========="
  echo "==========================================="

  /bin/wait-for-it.sh -t 0 $DB_HOST:5432 -- echo "Postgres is live"
fi

if [ ! -z $CLL_READ_ONLY ] && [ $CLL_READ_ONLY = "False" ]; then
  echo "==========================================="
  echo "============== Migrating app =============="
  echo "==========================================="

  python manage.py makemigrations
  python manage.py migrate
fi

echo "==========================================="
echo "============== Compiling app =============="
echo "==========================================="
if [ ! -z $DEBUG ] && [ $DEBUG = "False" ]; then
  python manage.py compilescss
  python manage.py collectstatic --noinput --clear --ignore=*.scss -v 0
  python manage.py compress
  python manage.py collectstatic --noinput --ignore=*.scss -v 0
  
  chown -R www-data:www-data /var/www/concept_lib_sites
else
  python manage.py compilescss --delete-files
  python manage.py collectstatic --clear --noinput -v 0

  chown -R www-data:www-data /var/www/concept_lib_sites
fi

echo "==========================================="
echo "=========== Starting application =========="
echo "==========================================="

rm -f /var/run/apache2/apache2.pid
rm -rf /run/httpd/* /tmp/httpd*
chmod -R 777 /tmp/* 2>/dev/null

echo $(printf 'Started Server @ %s' "$SERVER_NAME")

/usr/sbin/apache2ctl -DFOREGROUND
