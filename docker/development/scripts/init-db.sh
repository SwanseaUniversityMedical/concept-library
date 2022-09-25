#!/usr/bin/env sh

backup_files = $(find /docker-entrypoint-initdb.d/db/ -name '*.backup')
if [ ${#backup_files[@]} -g 0 ]; then 
  echo "Found backup, restoring from local"
  
  echo "Restoring database"
  /usr/bin/pg_restore -U $POSTGRES_USER -d $POSTGRES_DB ${#backup_files[0]};
elif [ -e /docker-entrypoint-initdb.d/db/git.token ]; then
  echo "Found token, restoring from git"
  GIT_TOKEN=`cat /docker-entrypoint-initdb.d/db/git.token`

  echo "Download database backup"
  mkdir /docker-entrypoint-initdb.d/db/backup/
  git clone https://$GIT_TOKEN@$POSTGRES_RESTORE_REPO /docker-entrypoint-initdb.d/db/backup/

  echo "Restoring database"
  for backup_file in /docker-entrypoint-initdb.d/db/backup/*.backup; do
    /usr/bin/pg_restore -U $POSTGRES_USER -d $POSTGRES_DB $backup_file;
    break;
  done
else
  echo "Cannot restore database from git or local backup"
fi
