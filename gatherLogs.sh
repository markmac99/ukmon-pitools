#!/bin/bash
#
# Script to gather the logfiles and upload them for debugging & analysis
# Copyright (C) 2018-2023 Mark McIntyre
#
myself=$(readlink -f $0)
here="$( cd "$(dirname "$myself")" >/dev/null 2>&1 ; pwd -P )"

[ "$1" == "" ] && echo "usage: ./gatherlogs.sh UKxxxxx" && exit
CAMID=$1

cd $HOME
[ -d logtmp_$CAMID ] && rm -Rf logtmp_$CAMID
mkdir -p logtmp_$CAMID
cd logtmp_$CAMID

source $here/ukmon.ini

echo "gathering files"
# gather system logs
sudo cp /var/log/kern.log .
[ -f /var/log/messages ] && sudo cp /var/log/messages ./messages.log; 
[ -f /var/log/syslog ] && sudo cp /var/log/syslog ./messages.log
sudo chown ${LOGNAME}:${LOGNAME} ./*.log

# find the RMS config and log location
if [ -d /home/${LOGNAME}/source/Stations/${CAMID} ] ; then
    rootdir=/home/${LOGNAME}/source/Stations/${CAMID}
else
    rootdir=/home/${LOGNAME}/source/RMS
fi 
echo rootdir is $rootdir
rmscfg=$rootdir/.config
datadir=$(python -c "import configparser,os;cfg=configparser.ConfigParser();cfg.read('$rmscfg');print(os.path.expanduser(cfg['Capture']['data_dir']))")
logdir=$datadir/logs
echo logdir is $logdir
[ ! -d $logdir ] && logdir=~/RMS_data/logs

# gather the RMS config and logs
cp $rootdir/.config ./${CAMID}.config
cp $rootdir/platepar_cmn2010.cal ./${CAMID}.cal
cp $here/live.key ./${CAMID}.key
cp $here/ukmon.ini .
[ -f $here/cameras.ini ] && cp $here/cameras.ini .
crontab -l > ./crontab.txt
ls -1tr $logdir/log*.log* | tail -5 | while read i; do cp $i . ; done
ls -1tr $logdir/uk*.log* | tail -5 | while read i; do cp $i . ; done

# create a tarball and upload to the server
echo "uploading logs"
ZIPFILE=/tmp/${CAMID}_logs.tgz
tar czf $ZIPFILE *.log* ${CAMID}.config ${CAMID}.cal crontab.txt *.key *.ini
sftp -i $UKMONKEY -q logupload@$UKMONHELPER << EOF
cd logs
progress
put $ZIPFILE 
exit
EOF
cd ..
rm -Rf logtmp_$CAMID
echo "done"