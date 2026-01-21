#!/usr/bin/env sh

# Restore from backup
if [ -z $IS_TEST_ENV ] || [ $TEST_ENV = "False" ]; then
  echo "====================================";
  echo "== Attempting to restore database ==";
  echo "====================================";

  SQL_FILE=$(find /docker-entrypoint-initdb.d/db/ -name '*.sql'| head -1);
  BACKUP_FILE=$(find /docker-entrypoint-initdb.d/db/ -name '*.backup'| head -1);
  if [ ! -z $BACKUP_FILE ] && [ -e $BACKUP_FILE ]; then 
    echo "[!>] Found dump backup, restoring from local";
    echo "[!>] Restoring database from local .backup";

    /usr/bin/pg_restore -U $POSTGRES_USER -d $POSTGRES_DB $BACKUP_FILE;
  elif [ ! -z $SQL_FILE ] && [ -e $SQL_FILE ]; then 
    echo "[!>] Found sql backup, restoring from local";
    echo "[!>] Restoring database from local .sql";
    /usr/bin/psql -U $POSTGRES_USER -d $POSTGRES_DB -f $SQL_FILE;
  elif [ -e /docker-entrypoint-initdb.d/db/git.token ]; then
    echo "[!>] Found token, restoring from git";
    GIT_TOKEN=`cat /docker-entrypoint-initdb.d/db/git.token`;

    if [ -d "/docker-entrypoint-initdb.d/db/backup/" ]; then
      echo "[!>] Aborting restore, please remove './docker/development/db/backup/' folder";
    else
      echo "[!>] Downloading git repository";
      mkdir /docker-entrypoint-initdb.d/db/backup/;
      git clone https://$GIT_TOKEN@$POSTGRES_RESTORE_REPO /docker-entrypoint-initdb.d/db/backup/;

      BACKUP_FILE=$(find /docker-entrypoint-initdb.d/db/backup/ -name '*.backup'| head -1);
      if [ ! -z $BACKUP_FILE ] && [ -e $BACKUP_FILE ]; then 
        echo "[!>] Restoring database from cloned .backup file";
        mv $BACKUP_FILE /docker-entrypoint-initdb.d/db/db.backup;
        rm -rf /docker-entrypoint-initdb.d/db/backup/;

        /usr/bin/pg_restore -U $POSTGRES_USER -d $POSTGRES_DB /docker-entrypoint-initdb.d/db/db.backup;
      else
        echo "[!>] Cannot restore, failed to find database file after cloning repo";
      fi
    fi
  else
    echo "[!>] Cannot restore database from git or local backup";
  fi
fi

# Attempt to create test user if required by environment
echo "====================================";
echo "==    Attempting add test user    ==";
echo "====================================";

echo "
do \$bd\$
  begin
    create user $UNIT_TEST_DB_USER
      with createdb
            password '$UNIT_TEST_DB_PASSWORD';

    raise notice '[ SUCCESS ] Created TestUser<usename: \"$UNIT_TEST_DB_USER\">';
  exception
    when sqlstate '42710' then
      raise notice '[ INFO ] TestUser<usename: \"$UNIT_TEST_DB_USER\"> exists';
    when others then
      raise;
  end
\$bd\$;" | /usr/bin/psql -U $POSTGRES_USER -d $POSTGRES_DB;

echo "====================================";
echo "==       Forcing extensions       ==";
echo "====================================";

echo "
do \$bd\$
  begin
    create extension if not exists pg_trgm;
    create extension if not exists btree_gin;
    create extension if not exists fuzzystrmatch;

    raise notice '[ SUCCESS ] Forced pg_trgm, btree_gin & fuzzystrmatch';
  end
\$bd\$;" | /usr/bin/psql -U $POSTGRES_USER -d $POSTGRES_DB;
