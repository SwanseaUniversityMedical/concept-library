#!/usr/bin/env sh

echo "===================================="
echo "== Attempting to restore database =="
echo "===================================="

BACKUP_FILE=$(find /docker-entrypoint-initdb.d/db/ -name '*.backup'| head -1)
if [ ! -z $BACKUP_FILE ] && [ -e $BACKUP_FILE ]; then 
  echo "[!>] Found backup, restoring from local"
  echo "[!>] Restoring database from local .backup"
  /usr/bin/pg_restore -U $POSTGRES_USER -d $POSTGRES_DB $BACKUP_FILE;
elif [ -e /docker-entrypoint-initdb.d/db/git.token ]; then
  echo "[!>] Found token, restoring from git"
  GIT_TOKEN=`cat /docker-entrypoint-initdb.d/db/git.token`

  if [ -d "/docker-entrypoint-initdb.d/db/backup/" ]; then
    echo "[!>] Aborting restore, please remove './docker/development/db/backup/' folder"
  else
    echo "[!>] Downloading git repository"
    mkdir /docker-entrypoint-initdb.d/db/backup/
    git clone https://$GIT_TOKEN@$POSTGRES_RESTORE_REPO /docker-entrypoint-initdb.d/db/backup/

    BACKUP_FILE=$(find /docker-entrypoint-initdb.d/db/backup/ -name '*.backup'| head -1)
    if [ ! -z $BACKUP_FILE ] && [ -e $BACKUP_FILE ]; then 
      echo "[!>] Restoring database from cloned .backup file"
      mv $BACKUP_FILE /docker-entrypoint-initdb.d/db/db.backup
      rm -rf /docker-entrypoint-initdb.d/db/backup/

      /usr/bin/pg_restore -U $POSTGRES_USER -d $POSTGRES_DB /docker-entrypoint-initdb.d/db/db.backup

    else
      echo "[!>] Cannot restore, failed to find database file after cloning repo"
    fi
  fi
else
  echo "[!>] Cannot restore database from git or local backup"
fi
