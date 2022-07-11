FROM postgres:9.4.26

COPY ./init-user-db.sh /docker-entrypoint-initdb.d/init-user-db.sh
COPY ./demo-16-06-2022.backup /docker-settings/backupfiletoput

EXPOSE 5432/tcp

