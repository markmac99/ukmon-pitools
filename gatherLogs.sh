#!/bin/bash
cd ~/RMS_data/logs
mkdir logtmp
cd logtmp

#
# Script to gather the logfiles and upload them for debugging & analysis
# Copyright (C) 2018-2023 Mark McIntyre
#
source /home/${LOGNAME}/source/ukmon-pitools/ukmon.ini
sudo cp /var/log/kern.log .
sudo chown $:{user}:${LOGNAME} kern.log
cp /var/log/messages ./messages.log
cp /home/${LOGNAME}/source/RMS/.config ./${LOCATION}.config
cp /home/${LOGNAME}/source/RMS/platepar_cmn2010.cal ./${LOCATION}.cal
cp /home/${LOGNAME}/source/ukmon-pitools/*.key .
cp /home/${LOGNAME}/source/ukmon-pitools/*.ini .
crontab -l > ./crontab.txt
find  .. -maxdepth 1 -name "*.log*" -type f -mtime -5 -exec cp {} . \;
ZIPFILE=/tmp/${LOCATION}_logs.tgz
tar cvzf $ZIPFILE *.log* ${LOCATION}.config ${LOCATION}.cal crontab.txt *.key *.ini
sftp -i $UKMONKEY -q logupload@$UKMONHELPER << EOF
cd logs
progress
put $ZIPFILE 
exit
EOF
cd ..
rm -Rf logtmp
