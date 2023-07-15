FROM python:3.9-slim-bullseye

ENV PYTHONUNBUFFERED 1
ENV LC_ALL=C.UTF-8

# Update packages
RUN \
  apt-get update -y -q && \
  apt-get upgrade -y -q && \
  apt-get install -y -q dos2unix libsasl2-dev libldap2-dev libssl-dev

# Set main workdir
WORKDIR /var/www

# Install & upgrade pip
RUN \
  apt-get install -y -q python3-pip

RUN \
  pip install --upgrade pip

# Copy & Install requirements
RUN mkdir -p /var/www/concept_lib_sites/v1
COPY ./requirements /var/www/concept_lib_sites/v1/requirements
RUN ["chown", "-R" , "www-data:www-data", "/var/www/concept_lib_sites/"]

RUN pip --no-cache-dir install -r /var/www/concept_lib_sites/v1/requirements/base.txt

# Deploy scripts
COPY ./production/scripts/worker-start.sh /home/config_cll/worker-start.sh
COPY ./production/scripts/beat-start.sh /home/config_cll/beat-start.sh

RUN ["chmod" , "+x" , "/home/config_cll/worker-start.sh"]
RUN ["chmod" , "+x" , "/home/config_cll/beat-start.sh"]

COPY ./development/scripts/wait-for-it.sh /bin/wait-for-it.sh
RUN ["chmod", "u+x", "/bin/wait-for-it.sh"]
RUN ["dos2unix", "/bin/wait-for-it.sh"]
