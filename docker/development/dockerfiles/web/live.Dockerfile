FROM python:3.10-slim-bookworm

ARG server_name
ARG dependency_target

ENV SERVER_NAME=$server_name
ENV DEPENDENCY_TARGET=$dependency_target

ENV LC_ALL=C.UTF-8
ENV PYTHONUNBUFFERED=1

# Update package tool
RUN apt-get update -y -q \
  && apt-get upgrade -y -q \
  && apt-get install -y -q --no-install-recommends apt-utils

# Install apache & deps
RUN apt-get install -y -q ssh apache2 apache2-dev

# Install supervisor
RUN apt-get install -y -q supervisor

# Install misc deps
RUN apt-get install -y -q wget sudo nano dos2unix curl ca-certificates

# Install LDAP deps
RUN apt-get install -y -q libsasl2-dev libldap2-dev libssl-dev

# Install npm
RUN apt-get update && apt-get install -y \
    software-properties-common \
    npm

# Install esbuild
RUN npm install -g config set user root

RUN npm install -g esbuild@0.19.0

# Instantiate log dir
RUN ["mkdir", "-p", "/home/config_cll/cll_srvr_logs"]
RUN ["chmod", "750", "/home/config_cll/cll_srvr_logs"]

# Set main workdir
WORKDIR /var/www

# Copy & install requirements
RUN mkdir -p /var/www/concept_lib_sites/v1
COPY ./requirements /var/www/concept_lib_sites/v1/requirements
RUN ["chown" , "-R" , "www-data:www-data",  "/var/www/concept_lib_sites/"]

# Install pip & upgrade pip then install deps
RUN apt-get install -y -q python3-pip \
  && pip install --upgrade pip

RUN pip --no-cache-dir install -r /var/www/concept_lib_sites/v1/requirements/$DEPENDENCY_TARGET

# User perms
RUN ["chown" , "-R" , "www-data:www-data" , "/bin/"]
RUN ["chown" , "-R" , "www-data:www-data" , "/var/www/"]
RUN ["chown" , "-R" , "www-data:www-data" , "/home/config_cll/"]
RUN ["chown" , "-R" , "www-data:www-data" , "/home/config_cll/cll_srvr_logs"]

# Utility scripts
COPY ./development/scripts/wait-for-it.sh /bin/wait-for-it.sh
RUN ["chmod", "a+x", "/bin/wait-for-it.sh"]
RUN ["dos2unix", "/bin/wait-for-it.sh"]

COPY ./development/scripts/healthcheck.sh /bin/web-healthcheck.sh
RUN ["chmod", "a+x", "/bin/web-healthcheck.sh"]
RUN ["dos2unix", "/bin/web-healthcheck.sh"]

# Deploy scripts
COPY ./production/scripts/init-app.sh /home/config_cll/init-app.sh
COPY ./production/scripts/worker-start.sh /home/config_cll/worker-start.sh
COPY ./production/scripts/beat-start.sh /home/config_cll/beat-start.sh

RUN ["chmod" , "a+x" , "/home/config_cll/worker-start.sh"]
RUN ["dos2unix", "/home/config_cll/worker-start.sh"]

RUN ["chmod" , "a+x" , "/home/config_cll/beat-start.sh"]
RUN ["dos2unix", "/home/config_cll/beat-start.sh"]

RUN ["chmod", "+x", "/home/config_cll/init-app.sh"]
RUN ["dos2unix", "/home/config_cll/init-app.sh"]

RUN ["chmod", "750", "/home/config_cll"]

# Config apache
RUN echo $(printf 'export SERVER_NAME=%s' "$SERVER_NAME") >> /etc/apache2/envvars
RUN echo $(printf 'ServerName %s' "$SERVER_NAME") >> /etc/apache2/apache2.conf

# Set up wsgi
RUN mod_wsgi-express module-config >> /etc/apache2/apache2.conf

# Enable site
ADD ./production/config/cll.apache.conf /etc/apache2/sites-available/cll.conf

RUN \
  a2dissite \
    000-default && \
  a2enmod \
    env \
    rewrite \
    headers \
    proxy_http \
    expires && \
  a2ensite \
    cll.conf

# Set up supervisord
ADD ./production/config/cll.supervisord.conf /etc/supervisord.conf

# Set workdir to app
WORKDIR /var/www/concept_lib_sites/v1/CodeListLibrary_project
