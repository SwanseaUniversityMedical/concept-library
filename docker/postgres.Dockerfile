FROM postgres:14.4

# Install and upgrade packages
RUN apt-get update -y -q && \
    apt-get install git -y -q

COPY ./development/scripts/init-db.sh /docker-entrypoint-initdb.d/init-db.sh
RUN ["chmod", "u+x", "/docker-entrypoint-initdb.d/init-db.sh"]
