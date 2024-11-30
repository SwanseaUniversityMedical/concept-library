####################################
##                                ##
##              Base              ##
##                                ##
####################################
FROM python:3.10-slim-bookworm AS base

ARG http_proxy
ARG https_proxy
ARG server_name
ARG dependency_target

ENV HTTP_PROXY=$http_proxy
ENV HTTPS_PROXY=$https_proxy
ENV SERVER_NAME=$server_name

ENV LC_ALL=C.UTF-8
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# Install packages
RUN apt-get update -y -q && \
    apt-get upgrade -y -q && \
    apt-get install -y -q --no-install-recommends \
      wget curl ca-certificates apt-utils  `# Base deps`           \
      cmake build-essential python3-pip git                        \
      ssh apache2 apache2-dev supervisor   `# Apache & Supervisor` \
      libsasl2-dev libldap2-dev libssl-dev `# LDAP deps`           \
      software-properties-common npm       `# Npm deps`

# Create dir(s)
RUN mkdir -p /var/www/concept_lib_sites/v1 && \
    mkdir -p /home/config_cll/cll_srvr_logs

# Copy script volume(s)
COPY ./docker/app/scripts/build /bin/scripts
COPY ./docker/app/scripts/init /home/config_cll/init
COPY ./docker/app/scripts/health /home/config_cll/health

# Copy dependency target(s)
COPY ./docker/requirements /var/www/concept_lib_sites/v1/requirements

# Copy app volume(s)
COPY ./engagelens /var/www/concept_lib_sites/v1/engagelens
COPY ./CodeListLibrary_project /var/www/concept_lib_sites/v1/CodeListLibrary_project

# Set perms
RUN chown -R www-data:www-data /var/www/ /home/config_cll && \
    chmod -R 750 /home/config_cll

RUN find /bin/scripts -type f -iname "*.sh" -exec chmod a+x {} \; -exec dos2unix {} \; && \
    find /home/config_cll -type f -iname "*.sh" -exec chmod a+x {} \; -exec dos2unix {} \;

# Config & install dependencies
RUN /bin/scripts/dependencies.sh /var/www/concept_lib_sites/v1/requirements/${dependency_target:-production.txt}


####################################
##                                ##
##              Dev               ##
##                                ##
####################################
FROM base AS dev
WORKDIR /var/www/concept_lib_sites/v1/CodeListLibrary_project


####################################
##                                ##
##              Prod              ##
##                                ##
####################################
FROM base AS prod

# Config supervisord
ADD ./docker/app/config/cll.supervisord.conf /etc/supervisord.conf

# Config apache
RUN echo $(printf 'export SERVER_NAME=%s' "$SERVER_NAME") >> /etc/apache2/envvars && \
    echo $(printf 'ServerName %s' "$SERVER_NAME") >> /etc/apache2/apache2.conf && \
    mod_wsgi-express module-config >> /etc/apache2/apache2.conf

# Enable site
ADD ./docker/app/config/cll.apache.conf /etc/apache2/sites-available/cll.conf

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

# Set workdir to app
WORKDIR /var/www/concept_lib_sites/v1/CodeListLibrary_project
