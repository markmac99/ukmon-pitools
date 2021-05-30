#!/bin/bash
cd ~/RMS_data/logs

#
# Script to gather the logfiles and upload them for debugging & analysis
#
source /home/pi/source/ukmon-pitools/ukmon.ini
sudo cp /var/log/kern.log .
sudo chown pi:pi kern.log
cp /var/log/messages ./messages.log
ZIPFILE=/tmp/${LOCATION}_logs.tgz
tar cvzf $ZIPFILE *.log*
sftp -i $UKMONKEY -q logupload@$UKMONHELPER << EOF
cd logs
progress
put $ZIPFILE 
exit
EOF
rm kern.log messages.log $ZIPFILE
