FROM python:3.9-slim

# Install and update packages
RUN apt-get update -y -q && \
    apt-get upgrade -y -q

# Install LDAP header files
RUN apt-get install -y -q libsasl2-dev python-dev libldap2-dev libssl-dev

# Install pip
RUN apt-get install -y -q python3-pip 

# Install Python packages
COPY ./requirements/ /home/requirements/
RUN pip install -r /home/requirements/local.txt
