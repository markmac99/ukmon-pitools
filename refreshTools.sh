#!/bin/bash

# refresh UKmeteornetwork tools
# Copyright (C) 2018-2023 Mark McIntyre

myself=$(readlink -f $0)
here="$( cd "$(dirname "$myself")" >/dev/null 2>&1 ; pwd -P )"
cd $here

export PYTHONPATH=$here:~/source/RMS
source ~/vRMS/bin/activate
# validate the ini file 
python -c "import ukmonInstaller as pp ; pp.validateIni('${here}', '3.8.65.98');"

# read in the config file
source $here/ukmon.ini

echo "refreshing toolset"
git stash 
git pull
git stash apply

echo "checking required python libs are installed"
pip list | grep boto3 || pip install boto3 
# python-crontab v2.5.1 for python 2.7 backwards compatability. Sigh. 
pip list | grep python-crontab | grep 2.5.1 || pip install python-crontab==2.5.1

# creating an ssh key if not already present
if [ ! -f  ${UKMONKEY} ] ; then 
    echo "creating ukmon ssh key"
    ssh-keygen -t rsa -f ${UKMONKEY} -q -N ''
    echo "Copy this public key and email it to the ukmon team, then "
    echo "wait for confirmation its been installed and rerun this script"
    echo ""
    cat ${UKMONKEY}.pub
    echo ""
    read -p "Press any key to continue"
fi

# if the station is configured, retrieve the AWS keys
# and test connectivity. 
if [[ "$LOCATION" != "NOTCONFIGURED"  && "$LOCATION" != "" ]] ; then
    sftp -i $UKMONKEY -q $LOCATION@$UKMONHELPER << EOF
put ukmon.ini ukmon.ini.client
get ukmon.ini .ukmon.new
get live.key
exit
EOF
    # compare the new and old ini files and update if needed
    # this allows remote updates to the location and server IP
    orighelp=$UKMONHELPER
    origloc=$LOCATION
    source .ukmon.new
    if [ "$UKMONHELPER" != "$orighelp" ] ; then
        export PYTHONPATH=$here:~/source/RMS
        python -c "import ukmonInstaller as pp ; pp.updateHelperIp('${here}','${UKMONHELPER}');"
        echo "server address updated"
    fi
    if [ "$LOCATION" != "$origloc" ] ; then 
        export PYTHONPATH=$here:~/source/RMS
        python -c "import ukmonInstaller as pp ; pp.updateLocation('${here}','${LOCATION}');"
        echo "camera location updated"
    fi
    rm -f .ukmon.new

    chmod 0600 live.key
    if [ -f archive.key ] ; then \rm archive.key ; fi 

    echo "checking the RMS config file, crontab and icons"
    source ~/vRMS/bin/activate
    source $here/ukmon.ini
    cd $(dirname $RMSCFG)
    export PYTHONPATH=$here:~/source/RMS
    python -c "import ukmonInstaller as pp ; pp.installUkmonFeed('${RMSCFG}');"

    echo "testing connections"
    python $here/sendToLive.py test test
    python $here/uploadToArchive.py test
    echo "if you did not see two success messages contact us for advice" 
    if [ "$DOCKER_RUNNING" != "true" ] ; then read -p "Press any key to finish" ; fi
    echo "done"
else
    statid=$(grep stationID $RMSCFG | awk -F" " '{print $2}')
    if [ "$statid" == "XX0001" ] ; then
        echo "You must configure RMS before setting up the ukmon tools"
    fi 
    python -c "import ukmonInstaller as pp ; pp.addDesktopIcons('${here}', '${statid}');"
    echo "Location missing - unable to continue. Please obtain a location code from the UKMON team,"
    echo "Update the UKMON Config File using the desktop icon then rerun this script."
    sleep 5
    if [ "$DOCKER_RUNNING" != "true" ] ; then read -p "Press any key to end" ; fi
    exit 1
fi

