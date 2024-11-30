FROM python:3.10-slim-bookworm

ARG http_proxy
ARG https_proxy

ENV HTTP_PROXY $http_proxy
ENV HTTPS_PROXY $https_proxy

ENV PYTHONUNBUFFERED 1
ENV LC_ALL=C.UTF-8
ENV DEBIAN_FRONTEND=noninteractive

# Set the working directory
WORKDIR /engagelens

# Install and update packages
RUN apt-get update -y -q && \
    apt-get upgrade -y -q && \
    apt-get install -y -q --no-install-recommends apt-utils dos2unix

# Copy env
COPY ./docker/requirements/engagelens.txt .
COPY ./engagelens .

RUN ["chown", "-R" , "www-data:www-data", "/engagelens/"]

# Install requirements & upgrade pip
RUN \
  apt-get install -y -q python3-pip

RUN \
  if [[ -z $HTTP_PROXY ]]; then \
    pip --proxy $HTTP_PROXY install --upgrade pip; \
    pip --proxy $HTTP_PROXY --no-cache-dir install -r engagelens.txt; \
  else \
    pip install --upgrade pip; \
    pip --no-cache-dir install -r engagelens.txt; \
  fi

# Make wait-for-it.sh executable
COPY ./docker/development/scripts/wait-for-it.sh /bin/wait-for-it.sh
RUN ["chmod", "+x", "/bin/wait-for-it.sh"]

# Convert the wait-for-it.sh script to Unix line endings (optional, if developed on Windows)
RUN ["dos2unix", "/bin/wait-for-it.sh"]
