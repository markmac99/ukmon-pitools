#!/bin/bash

# refresh UKmeteornetwork tools

here="$( cd "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
source $here/ukmon.ini

cd $here

sftp -i ~/.ssh/ukmon $LOCATION@$UKMONHELPER << EOF
get ukmon.ini
get live.key
get archive.key
exit
EOF
chmod 0600 live.key archive.key

echo "refreshing toolset"
git stash 
git pull
git stash apply

echo "checking boto3 is installed for AWS connections"
source ~/vRMS/bin/activate
noboto=$(pip list | grep boto3)
if [ $noboto == 1 ] ; then 
    pip install boto3
fi 
echo "done"
