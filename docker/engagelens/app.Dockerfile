FROM python:3.9-slim

ARG http_proxy
ARG https_proxy
ARG server_name

ENV HTTP_PROXY $http_proxy
ENV HTTPS_PROXY $https_proxy
ENV SERVER_NAME $server_name

ENV PYTHONUNBUFFERED 1
ENV LC_ALL=C.UTF-8

# Set the working directory
WORKDIR /engagelens


# Install and update packages
RUN apt-get update -y -q && \
    apt-get upgrade -y -q && \
    apt-get install dos2unix

COPY ./docker/requirements/engagelens.txt .
COPY ./engagelens .

RUN ["chown", "-R" , "www-data:www-data", "/engagelens/"]
# Install requirements
# Install & upgrade pip
RUN \
  apt-get install -y -q python3-pip

RUN pip --proxy http://192.168.10.15:8080 install --upgrade pip
RUN pip --proxy http://192.168.10.15:8080 --no-cache-dir install -r engagelens.txt

COPY ./docker/development/scripts/wait-for-it.sh /bin/wait-for-it.sh
# Make wait-for-it.sh executable
RUN ["chmod", "+x", "/bin/wait-for-it.sh"]
# Convert the wait-for-it.sh script to Unix line endings (optional, if developed on Windows)
RUN ["dos2unix", "/bin/wait-for-it.sh"]

