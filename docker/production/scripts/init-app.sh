#!/bin/bash

# Utils
ansi_cyan="$(printf '\e[1;36m')"
ansi_green="$(printf '\e[0;32m')"
ansi_yellow="$(printf '\e[0;33m')"
ansi_white="$(printf '\e[1;37m')"

wrap_cmd() {
  echo $(printf '%s[ Stage: %s%s / %s %s] [ %s%s%s ] Running command...\n' \
    "$ansi_white" "$ansi_cyan" "$(($1 - 1))" "$2" \
    "$ansi_white" "$ansi_yellow" "$3" "$ansi_white") >&2

  start_time=`date +%s`
    eval "${@: 4}"
  end_time=`date +%s`

  runtime=$(($end_time-$start_time))
  echo $(printf '%s[ Stage: %s%d / %d %s] [ %s%s %s] Completed after %s%ss\n' \
    "$ansi_white" "$ansi_cyan" "$1" "$2" \
    "$ansi_white" "$ansi_yellow" "$3" \
    "$ansi_white" "$ansi_green" "$runtime" ) >&2
}

# Workdir
cd /var/www/concept_lib_sites/v1/CodeListLibrary_project

# Initialise app
if [ ! -z $AWAIT_POSTGRES ] && [ $AWAIT_POSTGRES = "True" ]; then
  echo "==========================================="
  echo "========== Waiting for Postgres ==========="
  echo "==========================================="

  /bin/wait-for-it.sh -t 0 $DB_HOST:5432 -- echo "Postgres is live"
fi

echo "==========================================="
echo "=========== Clear static files ============"
echo "==========================================="

if [ ! -d "staticroot" ]; then
  rm -rf staticroot
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

chown -R www-data:www-data /var/www/concept_lib_sites

if [ ! -z $DEBUG ] && [ $DEBUG = "False" ]; then
  max_stage=3

  wrap_cmd "1" "$max_stage" "Compiling SCSS"         "python manage.py compilescss --verbosity=0"
  wrap_cmd "2" "$max_stage" "Compressing assets"     "python manage.py compress --force --verbosity=0"
  wrap_cmd "3" "$max_stage" "Collecting staticfiles" "python manage.py collectstatic --noinput --no-post-process -v 0"

  # python manage.py compilescss
  # python manage.py collectstatic --noinput --clear -v 0
  # python manage.py compress
  # python manage.py collectstatic --noinput -v 0
else
  python manage.py compilescss --delete-files
  python manage.py collectstatic --clear --noinput -v 0
fi

echo "==========================================="
echo "=========== Starting application =========="
echo "==========================================="

rm -f /var/run/apache2/apache2.pid
rm -rf /run/httpd/* /tmp/httpd*
chmod -R 777 /tmp/* 2>/dev/null

echo $(printf 'Started Server @ %s' "$SERVER_NAME")

/usr/sbin/apache2ctl -DFOREGROUND
