FROM python:3.9-slim-bullseye

ARG http_proxy
ARG https_proxy
ENV HTTP_PROXY $http_proxy
ENV HTTPS_PROXY $https_proxy

ENV PYTHONUNBUFFERED 1
ENV LC_ALL=C.UTF-8

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
  apt-get install -y -q dos2unix && \
  apt-get install -y -q curl && \
  apt-get install -y -q npm && \
  apt-get install -y -q ca-certificates

# Install LDAP deps
RUN apt-get install -y -q libsasl2-dev libldap2-dev libssl-dev

# Install npm
RUN apt-get update && apt-get install -y \
    software-properties-common \
    npm

# Install esbuild
RUN curl -fsSL --proxy https://192.168.10.15:8080 https://deb.nodesource.com/setup_18.x | sudo bash -E - && \
  apt-get install -y nodejs

RUN npm config set proxy http://192.168.10.15:8080 && \
    npm config set https-proxy https://192.168.10.15:8080 && \
    npm config set registry http://registry.npmjs.org/ && \
    npm install -g config set user root \
    npm install -g esbuild

# Install & upgrade pip
RUN \
  apt-get install -y -q python3-pip

RUN \
  pip --proxy http://192.168.10.15:8080 install --upgrade pip

RUN mkdir -p /home/config_cll/cll_srvr_logs
RUN chmod 750 /home/config_cll/cll_srvr_logs

WORKDIR /var/www

# Copy & Install requirements
RUN mkdir -p /var/www/concept_lib_sites/v1
COPY ./requirements /var/www/concept_lib_sites/v1/requirements

RUN pip --proxy http://192.168.10.15:8080 --no-cache-dir install -r /var/www/concept_lib_sites/v1/requirements/base.txt

# Deploy scripts
COPY ./production/scripts/init-app.sh /home/config_cll/init-app.sh
COPY ./production/scripts/worker_start.sh /home/config_cll/worker_start.sh
COPY ./production/scripts/beat_start.sh /home/config_cll/beat_start.sh

RUN ["chmod" , "+x" , "/home/config_cll/init-app.sh"]
RUN ["chmod" , "+x" , "/home/config_cll/worker_start.sh"]
RUN ["chmod" , "+x" , "/home/config_cll/beat_start.sh"]
RUN ["chown" , "-R" , "www-data:www-data" , "/var/www/"]

COPY ./development/scripts/wait-for-it.sh /bin/wait-for-it.sh
RUN ["chmod", "u+x", "/bin/wait-for-it.sh"]
RUN ["dos2unix", "/bin/wait-for-it.sh"]

# Config apache
COPY ./production/cll.conf /etc/apache2/sites-available/cll.conf
RUN a2enmod wsgi

# Enable the site
RUN \
  cd /etc/apache2/sites-available && \
  a2ensite cll && \
  a2dissite 000-default.conf && \
  a2enmod rewrite

# Expose ports
EXPOSE 80
EXPOSE 443
