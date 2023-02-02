#!/bin/sh
echo ">>>>> STARTING (production server deployment) <<<<<<<<<<<<<<<<<<<"

#http_proxy=http://192.168.10.15:8080;
#export http_proxy

#https_proxy=https://192.168.10.15:8080;
#export https_proxy


#      echo ">>>>> update .ini file (to be  arranged later)<<<<<<<<<<<<<<<<<<<"

echo ">>>>> open project's virtual env <<<<<<<<<<<<<<<<<<<"
cd /var/www/concept_lib_sites/v1
#virtualenv --python=/usr/bin/python2.7 cllvirenv_v1
##source cllvirenv_v1/bin/activate  # for bash
echo ">>>>> virtualenv   <<<<<<<<<"
. cllvirenv_v1/bin/activate   # for sh
echo `pwd`

#echo ">>>>> install requirements <<<<<<<<<<<<<<<<<<<"
#cd /var/www/concept_lib_sites/v1/requirements

#pip --proxy http://192.168.10.15:8080 install --upgrade "pip < 19.1"
#pip --proxy http://192.168.10.15:8080 install -r base.txt

#pip --proxy http://192.168.10.15:8080 install psycopg2-binary

cd /var/www/concept_lib_sites/v1/CodeListLibrary_project

echo ">>>>> compilescss <<<<<<<<<<<<<<<<<<"
python manage.py compilescss

echo ">>>>> collectstatic <<<<<<<<<<<<<<<<<<<"
python manage.py collectstatic --noinput 1> /dev/null

echo ">>>>> makemigrations <<<<<<<<<<<<<<<<<<<"
python manage.py makemigrations

echo ">>>>> migrate <<<<<<<<<<<<<<<<<<<"
python manage.py migrate

#      echo ">>>>>Redis server start <<<<<<<<"
#      service redis-server restart

#      echo ">>>>>> Start celery worker <<<<<"
#      celery -A cll worker -l INFO

#      echo ">>>>> Start beat scheduler <<<<<<<<"
#      celery -A cll beat -l INFO


#     exit virtual env
deactivate

#echo ">>>>> restart apache <<<<<<<<<<<<<<<<<<<"
#/etc/init.d/apache2 restart

echo "Done!"

#exec "$@"
