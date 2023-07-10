#!/usr/bin/env sh

echo "===================================="
echo "======= Starting application ======="
echo "===================================="

if [ ! -z $DEBUG ] && [ $DEBUG = 0 ]; then
  echo "[!>] Starting dev app [TEST_STATIC_SERVING: TRUE]"
  python /var/www/CodeListLibrary_project/manage.py migrate
  python /var/www/CodeListLibrary_project/manage.py compilescss
  python /var/www/CodeListLibrary_project/manage.py collectstatic --noinput --clear
  python /var/www/CodeListLibrary_project/manage.py compress
  python /var/www/CodeListLibrary_project/manage.py collectstatic --noinput
  python /var/www/CodeListLibrary_project/manage.py runserver 0.0.0.0:8000 --nostatic
else
  echo "[!>] Starting dev app [TEST_STATIC_SERVING: FALSE]"
  python /var/www/CodeListLibrary_project/manage.py migrate
  python /var/www/CodeListLibrary_project/manage.py runserver 0.0.0.0:8000
fi
