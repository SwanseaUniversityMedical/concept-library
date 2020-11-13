FROM amd64/debian:stretch AS base

ARG DEBIAN_FRONTEND=noninteractive

EXPOSE 80
EXPOSE 443

ENV http_proxy=http://192.168.10.15:8080 
ENV https_proxy=http://192.168.10.15:8080

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
  pip --proxy http://192.168.10.15:8080 install  --upgrade pip 

RUN \
  pip install virtualenv && \
  pip install psycopg2-binary

RUN mkdir -p /home/config_cll/cll_srvr_logs
RUN chmod 750 /home/config_cll/cll_srvr_logs




