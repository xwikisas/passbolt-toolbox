#!/bin/sh

HTDIGEST_PATH=/etc/apache2/htdigest
HTDIGEST_BACKUP_PATH=/etc/apache2/htdigest.old

# Rollback the file
mv $HTDIGEST_BACKUP_PATH $HTDIGEST_PATH
