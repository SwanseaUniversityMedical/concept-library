FROM python:3.9-slim

ENV PYTHONUNBUFFERED 1
ENV LC_ALL=C.UTF-8

EXPOSE 80
EXPOSE 443

# Update packages
RUN \
  apt-get update -y -q && \
  apt-get upgrade -y -q && \
  apt-get install -y -q --no-install-recommends apt-utils && \
  apt-get install -y -q ssh apache2 && \
  apt-get install -y -q libapache2-mod-wsgi-py3 && \
  apt-get install -y -q wget && \
  apt-get -y -q install sudo nano && \
  apt-get install -y -q redis-server && \ 
  apt-get install -y -q dos2unix

# Install LDAP deps
RUN apt-get install -y -q libsasl2-dev libldap2-dev libssl-dev

# Install npm
RUN apt-get update && apt-get install -y \
    software-properties-common \
    npm

# Install esbuild
RUN npm install -g config set user root \
    npm install -g esbuild

# Install & upgrade pip
RUN \
  apt-get install -y -q python3-pip

RUN \
  pip install --upgrade pip

RUN mkdir -p /home/config_cll/cll_srvr_logs
RUN chmod 750 /home/config_cll/cll_srvr_logs

WORKDIR /var/www/

# Copy requirements
RUN mkdir -p /var/www/concept_lib_sites/v1
COPY ./requirements /var/www/concept_lib_sites/v1/requirements

RUN \
  pip --no-cache-dir install -r /var/www/concept_lib_sites/v1/requirements/base.txt

# Config apache
COPY ./production/cll.conf /etc/apache2/sites-available/cll.conf
# RUN echo "ServerName localhost" >> /etc/apache2/apache2.conf
RUN a2enmod wsgi

# Enable the site
RUN \
  cd /etc/apache2/sites-available && \
  a2ensite cll  && \
  a2dissite 000-default.conf && \
  a2enmod rewrite

# Deploy scripts
COPY ./production/scripts/init-app.sh /home/config_cll/init-app.sh

# Make file executable
RUN ["chmod" , "+x" , "/home/config_cll/init-app.sh"]
RUN ["chown" , "-R" , "www-data:www-data" , "/var/www/"]

COPY ./development/scripts/wait-for-it.sh /bin/wait-for-it.sh
RUN chmod u+x /bin/wait-for-it.sh
RUN dos2unix /bin/wait-for-it.sh

# ENTRYPOINT
# RUN ["/home/config_cll/init-app.sh"]
