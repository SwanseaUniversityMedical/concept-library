#!/usr/bin/env sh

BACKUP_FILE=$(find /docker-entrypoint-initdb.d/db/ -name '*.backup'| head -1)
if [ -e $BACKUP_FILE ]; then 
  echo "Found backup, restoring from local"
  
  echo "Restoring database"
  /usr/bin/pg_restore -U $POSTGRES_USER -d $POSTGRES_DB $BACKUP_FILE;
elif [ -e /docker-entrypoint-initdb.d/db/git.token ]; then
 echo "Found token, restoring from git"
 GIT_TOKEN=`cat /docker-entrypoint-initdb.d/db/git.token`

 echo "Download database backup"
 mkdir /docker-entrypoint-initdb.d/db/backup/
 git clone https://$GIT_TOKEN@$POSTGRES_RESTORE_REPO /docker-entrypoint-initdb.d/db/backup/

 echo "Restoring database"
 for backup_file in /docker-entrypoint-initdb.d/db/backup/*.backup; do
   echo "Found backup file"
   /usr/bin/pg_restore -U $POSTGRES_USER -d $POSTGRES_DB $backup_file;

   echo "Removing unneccessary files"
   mv $backup_file /docker-entrypoint-initdb.d/db/db.backup
   rm -rf /docker-entrypoint-initdb.d/db/backup/
   break;
 done
else
  echo "Cannot restore database from git or local backup"
fi
