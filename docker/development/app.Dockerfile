FROM python:3.9-slim

ENV PYTHONUNBUFFERED 1
ENV LC_ALL=C.UTF-8

# Install and update packages
RUN apt-get update -y -q && \
    apt-get upgrade -y -q && \
    apt-get install dos2unix

# Install LDAP header files
RUN apt-get install -y -q libsasl2-dev libldap2-dev libssl-dev

# Install npm
RUN apt-get update && apt-get install -y \
    software-properties-common \
    npm

# Install esbuild
RUN npm install -g config set user root

RUN npm install -g esbuild@0.19.0

# Set main workdir
WORKDIR /var/www

# Install & upgrade pip
RUN \
  apt-get install -y -q python3-pip && \
  pip install --upgrade pip

# Copy & Install requirements
RUN mkdir -p /var/www/concept_lib_sites/v1
COPY ./requirements /var/www/concept_lib_sites/v1/requirements
RUN ["chown", "-R" , "www-data:www-data", "/var/www/concept_lib_sites/"]

# Install requirements
RUN pip --no-cache-dir install -r /var/www/concept_lib_sites/v1/requirements/local.txt


# Deploy scripts
RUN ["chown" , "-R" , "www-data:www-data" , "/var/www/"]

COPY ./development/scripts/wait-for-it.sh /bin/wait-for-it.sh
RUN ["chmod", "u+x", "/bin/wait-for-it.sh"]
RUN ["dos2unix", "/bin/wait-for-it.sh"]

WORKDIR /var/www/concept_lib_sites/v1/CodeListLibrary_project/