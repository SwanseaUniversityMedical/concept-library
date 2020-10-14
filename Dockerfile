FROM cll/os AS base

ENV LC_ALL=C.UTF-8

WORKDIR /var/www/


######### copy code ######################
RUN mkdir -p /var/www/concept_lib_sites/v1


COPY requirements /var/www/concept_lib_sites/v1/requirements 
COPY CodeListLibrary_project/clinicalcode /var/www/concept_lib_sites/v1/CodeListLibrary_project/clinicalcode
COPY CodeListLibrary_project/cll /var/www/concept_lib_sites/v1/CodeListLibrary_project/cll
COPY CodeListLibrary_project/manage.py /var/www/concept_lib_sites/v1/CodeListLibrary_project/manage.py

#########################################
# config apache
COPY OS/cll.conf /etc/apache2/sites-available/cll.conf

RUN a2enmod wsgi

# enable the site
RUN \
  cd /etc/apache2/sites-available && \
  a2ensite cll  && \
  a2dissite 000-default.conf

# restart apache 
#RUN /etc/init.d/apache2 restart

#########################################

# Deploy script
COPY deploy_script_main.sh /home/config_cll/deploy_script_main.sh
COPY deploy_script_DB_mig.sh /home/config_cll/deploy_script_DB_mig.sh
COPY deploy_script_DB_mig_ro.sh /home/config_cll/deploy_script_DB_mig_ro.sh

# Make file executable:
RUN ["chmod" , "+x" , "/home/config_cll/deploy_script_main.sh"]
RUN ["chmod" , "+x" , "/home/config_cll/deploy_script_DB_mig.sh"]
RUN ["chmod" , "+x" , "/home/config_cll/deploy_script_DB_mig_ro.sh"]

RUN ["chown" , "-R" , "www-data:www-data" , "/var/www/"]
#RUN /home/config_cll/deploy_script_main.sh


#ENTRYPOINT ["/home/config_cll/deploy_script_main.sh"]
RUN ["/home/config_cll/deploy_script_main.sh"]

#*********************************************************************
#CMD ["/etc/init.d/apache2" ,"restart"]
CMD ["/usr/sbin/apache2ctl", "-D", "FOREGROUND"]

#RUN ["apache2ctl" , "restart"]

