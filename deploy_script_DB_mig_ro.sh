#!/bin/sh
      echo ">>>>> STARTING (production server deployment) <<<<<<<<<<<<<<<<<<<"

      http_proxy=$1;
      export http_proxy

      https_proxy=$2;
      export https_proxy
     

#      echo ">>>>> update .ini file (to be  arranged later)<<<<<<<<<<<<<<<<<<<"

      echo ">>>>> open project's virtual env <<<<<<<<<<<<<<<<<<<"
      cd /var/www/concept_lib_sites/v1
      virtualenv --python=/usr/bin/python2.7 cllvirenv_v1
      #source cllvirenv_v1/bin/activate  # for bash
      echo ">>>>> virtualenv   <<<<<<<<<"
      . cllvirenv_v1/bin/activate   # for sh
      echo `pwd`


      cd /var/www/concept_lib_sites/v1/CodeListLibrary_project
      
      echo ">>>>> collectstatic <<<<<<<<<<<<<<<<<<<"
      python manage.py collectstatic --noinput 1> /dev/null



#     exit virtual env
      deactivate

      #echo ">>>>> restart apache <<<<<<<<<<<<<<<<<<<"
      #/etc/init.d/apache2 restart

      echo "Done!"

      #exec "$@"
