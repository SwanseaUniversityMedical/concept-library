#!/bin/sh
      echo ">>>>> STARTING (production server deployment) <<<<<<<<<<<<<<<<<<<"

      #http_proxy=http://192.168.10.15:8080;
      #export http_proxy

      #https_proxy=https://192.168.10.15:8080;
      #export https_proxy

      #export pip_proxy="--proxy http://192.168.10.15:8080"
     

#      echo ">>>>> update .ini file (to be  arranged later)<<<<<<<<<<<<<<<<<<<"
      echo "@@@@@@@@@@ OS pip version="
      pip -V

      echo ">>>>> open project's virtual env <<<<<<<<<<<<<<<<<<<"
      cd /var/www/concept_lib_sites/v1
      virtualenv --python=/usr/bin/python2.7 cllvirenv_v1
      #source cllvirenv_v1/bin/activate  # for bash
      echo ">>>>> virtualenv   <<<<<<<<<"
      . cllvirenv_v1/bin/activate   # for sh
      echo `pwd`

      echo ">>>>> install requirements <<<<<<<<<<<<<<<<<<<"
      cd /var/www/concept_lib_sites/v1/requirements

      pip ${pip_proxy} install  pip-20.2-py2.py3-none-any.whl

      echo "@@@@@@@@@@ venv pip version="
      pip -V

      #pip ${pip_proxy} install --upgrade "pip < 19.1"
      pip ${pip_proxy} install -r base.txt

      pip ${pip_proxy} install psycopg2-binary
      pip2 ${pip_proxy} install pandas

      cd /var/www/concept_lib_sites/v1/CodeListLibrary_project

      #echo ">>>>> make migrations <<<<<<<<<<<<<<<<<<<"
      #python manage.py makemigrations  --settings=cll.settings
      #python manage.py migrate  --settings=cll.settings

      #echo ">>>>> collectstatic <<<<<<<<<<<<<<<<<<<"
      #python manage.py collectstatic --noinput 1> /dev/null

#     exit virtual env

      deactivate

      #echo ">>>>> restart apache <<<<<<<<<<<<<<<<<<<"
      #/etc/init.d/apache2 restart

      echo "Done!"

      #exec "$@"
