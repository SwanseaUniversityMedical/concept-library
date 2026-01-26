####################################
##                                ##
##              Args              ##
##                                ##
####################################
# Proxy config
ARG http_proxy
ARG https_proxy

# Image config
ARG TZ_PREF='Europe/London' \
    PY_VERSION='3.10' \
    DEB_RELEASE='bookworm'

# App config
ARG server_name='conceptlibrary.saildatabank.com' \
    dependency_target='production.txt'


####################################
##                                ##
##              Base              ##
##                                ##
####################################
FROM python:${PY_VERSION}-slim-${DEB_RELEASE} AS base
ARG TZ_PREF
ARG http_proxy
ARG https_proxy
ARG server_name

# Init env
ENV HTTP_PROXY=$http_proxy \
    HTTPS_PROXY=$https_proxy \
    SERVER_NAME=$server_name

ENV TZ="${TZ_PREF}" \
    LC_ALL=C.UTF-8 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

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

# Set perms
RUN chown -R www-data:www-data /var/www /home/config_cll && \
    chmod -R 750 /home/config_cll

# Cleanup
RUN apt-get autoremove -y -q && \
    apt-get clean -y -q


####################################
##                                ##
##             Build              ##
##                                ##
####################################
FROM base AS builder
ARG dependency_target

# Copy script volume(s)
COPY ./docker/app/scripts/build /bin/scripts
COPY ./docker/app/scripts/init /home/config_cll/init
COPY ./docker/app/scripts/health /home/config_cll/health

# Copy dependency target(s)
COPY ./docker/requirements /var/www/concept_lib_sites/v1/requirements

# Copy app volume(s)
COPY ./CodeListLibrary_project /var/www/concept_lib_sites/v1/CodeListLibrary_project

RUN find /bin/scripts -type f -iname "*.sh" -exec chmod a+x {} \; && \
    find /home/config_cll -type f -iname "*.sh" -exec chmod a+x {} \;

# Config & install dependencies
#> Install py deps
RUN if [ ! -z $HTTP_PROXY ] && [ -e $HTTP_PROXY ]; then \
      pip --proxy "$HTTP_PROXY" install --upgrade pip; \
      pip --proxy "$HTTP_PROXY" --no-cache-dir install -r "/var/www/concept_lib_sites/v1/requirements/${dependency_target:-production.txt}"; \
    else \
      pip install --upgrade pip; \
      pip --no-cache-dir install -r "/var/www/concept_lib_sites/v1/requirements/${dependency_target:-production.txt}"; \
    fi
#> Config NPM proxy if applicable
RUN if [ ! -z $HTTP_PROXY ] && [ -e $HTTP_PROXY ]; then \
      npm config set proxy "$HTTP_PROXY"; \
      npm config set https-proxy "$HTTPS_PROXY"; \
      npm config set registry "http://registry.npmjs.org/"; \
    fi
#> Install esbuild / other npm deps
RUN npm install -g config set user root
RUN npm install -g "esbuild@0.25.2"


####################################
##                                ##
##              Dev               ##
##                                ##
####################################
FROM builder AS dev

# Set workdir to app
WORKDIR /var/www/concept_lib_sites/v1/CodeListLibrary_project


####################################
##                                ##
##              Prod              ##
##                                ##
####################################
FROM builder AS prod

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
