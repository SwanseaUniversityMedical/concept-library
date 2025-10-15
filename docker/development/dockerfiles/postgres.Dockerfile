FROM postgres:17

# Install and upgrade packages
RUN apt-get update -y -q && \
    apt-get install git -y -q

COPY ./docker/development/scripts/init-db.sh /docker-entrypoint-initdb.d/init-db.sh

RUN chmod u+x /docker-entrypoint-initdb.d/init-db.sh
