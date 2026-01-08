#!/bin/bash

# refresh ukmon-pitools
# Copyright (C) 2018- Mark McIntyre

myself=$(readlink -f $0)
here="$( cd "$(dirname "$myself")" >/dev/null 2>&1 ; pwd -P )"

CAMID=$1
CAMID=${CAMID^^}

if [ "$CAMID" == "" ] ; then
    echo "Usage: ./setupUkmon.sh RMSID"
    echo "where 'RMSID' is your station's RMS ID eg UK12345"
    exit
fi 

export PYTHONPATH=$here:~/source/RMS
source ~/vRMS/bin/activate
cd $here

echo "refreshing toolset"
git config pull.ff only 
git stash 
git pull
git stash apply

UKMONKEY=~/.ssh/ukmon_$CAMID

if [ ! -f $here/ukmon.ini ] ; then
    echo "creating default ukmon ini file"
    python -c "from ukmonInstaller import createDefaultIni;createDefaultIni('$here', stationid='$CAMID');"
fi 

if [ ! -f $here/cameras.ini ] ; then
    echo "creating cameras.ini file"
    echo "# camera mapping file" > $here/cameras.ini
    echo "# echo add all cameras on this PC or Pi even if you only have one camera" >> $here/cameras.ini
    echo "[cameras]" >> $here/cameras.ini
fi
grep $CAMID $here/cameras.ini > /dev/null 2>&1
if [ $? == 1 ] ; then
    loc=$(python -c "from ukmonInstaller import findLocationFromOldIni;print(findLocationFromOldIni('$CAMID'))")
    echo "${CAMID}=${loc}" >> $here/cameras.ini
fi 

source $here/ukmon.ini
# creating an ssh key if not already present
if [ ! -f  ${UKMONKEY} ] ; then 
    echo "creating ukmon ssh key"
    ssh-keygen -t rsa -f ${UKMONKEY} -q -N ''
    echo "Now copy this public key and email it to newcamera@ukmeteornetwork.org, then "
    echo "wait for confirmation and further instructions to complete the setup."
    echo ""
    cat ${UKMONKEY}.pub
    echo ""
    read -p "Press any key to continue"
    exit
fi

echo "checking required python libs are installed"
pip list | grep boto3 || pip install boto3 
# python-crontab v2.5.1 for python 2.7 backwards compatability. Sigh. 
pip list | grep python-crontab | grep 2.5.1 || pip install python-crontab==2.5.1
pip list | grep paramiko || pip install paramiko

# get the location code from the cameras.ini file
LOCATION=$(grep $CAMID $here/cameras.ini)
LOCATION=$(echo $LOCATION | awk -F "=" '{print $2}')


# if the station is configured, retrieve the AWS keys and test connectivity. 
if [[ "$LOCATION" != "NOTCONFIGURED"  && "$LOCATION" != "" ]] ; then
    # check if RMS is still updating - its taking longer and longer
    loopctr=0
    echo "Checking RMS update not in progress"
    while [ $loopctr -lt 10 ] ; do
            [ -f $RMSCFG ] && break
            echo "RMS update in progress or station not configured, trying again in a minute"
            sleep 60
            loopctr=$((loopctr + 1))
    done
    while [ $loopctr -lt 10 ] ; do
            grep XX0001 $RMSCFG | grep stationID:
            [ $? -eq 1 ] && break
            echo "RMS update in progress or station not configured, trying again in a minute"
            sleep 60
            loopctr=$((loopctr + 1))
    done
    if [ $loopctr -eq 10 ] ; then
            echo RMS update failed or long-running, unable to proceed
            exit 1
    else
            echo all good proceeding
    fi
    echo "checking for ukmon config changes"
    python -c "import uploadToArchive as pp ; pp.getLatestKeys('${here}', '${stationid}') ;"
    
    if [ -d ~/Desktop ] ; then
        pushd ~/Desktop
        rm -f ukmon.ini UKMON_config* refreshTools* refresh_UKMON* > /dev/null 2>&1
    fi 
    echo "checking the RMS config file, crontab and icons"
    source ~/vRMS/bin/activate
    source $here/ukmon.ini
    export PYTHONPATH=$here:~/source/RMS
    python -c "import ukmonInstaller as pp ; pp.installUkmonFeed('${RMSCFG}');"

    echo "testing connections"
    python $here/sendToLive.py test test
    python $here/uploadToArchive.py test
    echo "if you did not see two success messages contact us for advice" 
    if [ "$DOCKER_RUNNING" != "true" ] ; then read -p "Press any key to finish" ; fi
    echo "done"
else
    echo $RMSCFG $CAMID
    statid=$(grep stationID $RMSCFG | awk -F" " '{print $2}')
    if [ "$statid" == "XX0001" ] ; then
        echo "You must configure RMS before setting up the ukmon tools"
    else
        #python -c "import ukmonInstaller as pp ; pp.addDesktopIcons('${here}', '${statid}');"
        echo "Location missing. Please obtain a location code from the UKMON team,"
        echo "then update cameras.ini and rerun this script."
    fi 
    sleep 5
    if [ "$DOCKER_RUNNING" != "true" ] ; then read -p "Press any key to end" ; fi
    exit 1
fi

