#!/bin/bash

cd /var/www/concept_lib_sites/v1/CodeListLibrary_project

if [ ! -z $IS_DEVELOPMENT_PC ] && [ $IS_DEVELOPMENT_PC = "True" ]; then
  echo "==========================================="
  echo "========== Waiting for Postgres ==========="
  echo "==========================================="

  /bin/wait-for-it.sh -t 0 $DB_HOST:5432 -- echo "Postgres is live"
fi

if [ ! -z $CLL_READ_ONLY ] && [ $CLL_READ_ONLY = "False" ]; then
  echo "==========================================="
  echo "============== Migrating app =============="
  echo "==========================================="

  python manage.py migrate
  python manage.py makemigrations
fi

echo "==========================================="
echo "============== Compiling app =============="
echo "==========================================="
if [ ! -z $DEBUG ] && [ $DEBUG = "True" ]; then
  python manage.py compilescss
  python manage.py collectstatic --noinput --clear --ignore=*.scss
  python manage.py compress
  python manage.py collectstatic --noinput --ignore=*.scss
  
  chown -R www-data:www-data /var/www/concept_lib_sites
else
  python manage.py compilescss
  python manage.py collectstatic --clear --noinput

  chown -R www-data:www-data /var/www/concept_lib_sites
fi

echo "==========================================="
echo "=========== Starting application =========="
echo "==========================================="

rm -f /var/run/apache2/apache2.pid
rm -rf /run/httpd/* /tmp/httpd*
chmod -R 777 /tmp/* 2>/dev/null
echo $(printf 'ServerName %s' "$SERVER_NAME") >> /etc/apache2/apache2.conf

exec "$@"
