#!/bin/sh

# exit when any command fails
set -e

HTDIGEST_PATH=/etc/apache2/htdigest
HTDIGEST_BACKUP_PATH=/etc/apache2/htdigest.old

# Rollback the file
if [ -f $HTDIGEST_BACKUP_PATH ] ; then
  mv $HTDIGEST_BACKUP_PATH $HTDIGEST_PATH
else
  echo 'No backup file found.' >&2
fi
