FROM amd64/debian:stretch AS base

ARG DEBIAN_FRONTEND=noninteractive

EXPOSE 80
EXPOSE 443

# update packages
RUN \
  apt-get update -y -q && \
  apt-get upgrade -y -q && \
  apt-get install -y -q --no-install-recommends apt-utils && \
  apt-get install -y -q ssh apache2 && \
  apt-get install -y -q libapache2-mod-wsgi && \
  apt-get -y -q install sudo nano


# install this for LDAP to work
RUN apt-get install -y -q libsasl2-dev python-dev libldap2-dev libssl-dev

##RUN apt-get install -y -q git

# install & upgrade pip
RUN \
  apt-get install -y -q python-pip 

RUN \
  pip  install  --upgrade pip 

RUN \
  pip install virtualenv && \
  pip install psycopg2-binary

RUN \
  mkdir -p /home/config_cll/cll_srvr_logs &&  \
  chmod 750 /home/config_cll/cll_srvr_logs










########################################################

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

# restart apache ....................
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

#**************************************************************************
#CMD ["/etc/init.d/apache2" ,"restart"]
CMD ["/usr/sbin/apache2ctl", "-D", "FOREGROUND"]

#RUN ["apache2ctl" , "restart"]
##########################################
#ENV http_proxy=
#ENV https_proxy=
