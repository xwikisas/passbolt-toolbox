#!/bin/sh

# exit when any command fails
set -e

# Verify that we have enough arguments
if [ "$#" -ge 3 ] ; then

HTDIGEST_USER=$1
HTDIGEST_REALM=$2
HTDIGEST_PASSWORD=$3

# Use fixed length paths to avoid $PATH spoofing
MD5SUM=/usr/bin/md5sum
AWK=/usr/bin/awk
HTDIGEST_PATH=/etc/apache2/htdigest
HTDIGEST_BACKUP_PATH=/etc/apache2/htdigest.old

# First, backup the htdigest file
if [ -f $HTDIGEST_PATH ] ; then
  cp $HTDIGEST_PATH $HTDIGEST_BACKUP_PATH
fi

(echo -n "$HTDIGEST_USER:$HTDIGEST_REALM:" \
 && echo -n "$HTDIGEST_USER:$HTDIGEST_REALM:$HTDIGEST_PASSWORD" \
 | $MD5SUM | $AWK '{print $1}') > $HTDIGEST_PATH
else
  echo 'Not enough arguments' >&2
  echo 'Usage : update_htdigest.sh user realm password'
fi
