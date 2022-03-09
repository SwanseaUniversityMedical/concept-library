#!/bin/sh
      cd /var/www/concept_lib_sites/v1
      virtualenv  cllvirenv_v1
      #source cllvirenv_v1/bin/activate  # for bash
      echo ">>>>> virtualenv   <<<<<<<<<"
      . cllvirenv_v1/bin/activate   # for sh
      echo `pwd`

      echo ">>>>> install requirements <<<<<<<<<<<<<<<<<<<"
      cd /var/www/concept_lib_sites/v1/requirements
      pip install --upgrade pip
      cat base.txt| xargs -n 1 pip install
      deactivate