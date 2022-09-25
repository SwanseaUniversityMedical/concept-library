FROM postgres:14.4

# Install and upgrade packages
RUN apt-get update -y -q && \
    apt-get upgrade -y -q && \
    apt-get install git -y -q
