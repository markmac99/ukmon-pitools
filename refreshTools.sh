#!/bin/bash

# refresh UKmeteornetwork tools

here=/home/$LOGNAME/source/ukmon-pitools
cd $here

# create a default config file if missing
if [ ! -f $here/ukmon.ini ] ; then
    echo  "# config data for this station" > $here/ukmon.ini
    echo  "export LOCATION=NOTCONFIGURED" >> $here/ukmon.ini
    echo  "export UKMONHELPER=3.8.65.98" >> $here/ukmon.ini
    echo  "export UKMONKEY=~/.ssh/ukmon" >> $here/ukmon.ini
    echo  "export RMSCFG=~/source/RMS/.config " >> $here/ukmon.ini
    echo "location not configured yet"
fi 
# read in the config file
source $here/ukmon.ini
# added 2022-05-04 to allow for non-standard config file locations
if [ "$RMSCFG" == "" ] ; then
    export RMSCFG=~/source/RMS/.config
fi 

echo "refreshing toolset"
git stash 
git pull
git stash apply

echo "checking required python libs are installed"
source ~/vRMS/bin/activate
pip list | grep boto3 || pip install boto3 
pip list | grep python-crontab || pip install python-crontab

# creating an ssh key if not already present
if [ ! -f  ~/.ssh/ukmon ] ; then 
    echo "creating ukmon ssh key"
    ssh-keygen -t rsa -f ~/.ssh/ukmon -q -N ''
    echo "Copy this public key and email it to the ukmon team, then "
    echo "wait for confirmation its been installed and rerun this script"
    echo ""
    cat ~/.ssh/ukmon.pub
    echo ""
    read -p "Press any key to continue"
fi

# if the station is configured, retrieve the AWS keys
# and test connectivity. Also checks the ukmon.ini file is in unix format
if [[ "$LOCATION" != "NOTCONFIGURED"  && "$LOCATION" != "" ]] ; then
    if [ $(file $here/ukmon.ini | grep CRLF | wc -l) -ne 0 ] ; then
        echo 'fixing ukmon.ini'
        cp $here/ukmon.ini $here/tmp.ini
        # dos2unix not installed on the pi
        tr -d '\r' < $here/tmp.ini > $here/ukmon.ini
        rm -f $here/tmp.ini
    fi 

    sftp -i $UKMONKEY -q $LOCATION@$UKMONHELPER << EOF
get ukmon.ini
get live.key
exit
EOF
    echo "get platepar_cmn2010.cal /tmp/platepar_cmn2010.cal" | sftp -b - -i $UKMONKEY -q $LOCATION@$UKMONHELPER > /dev/null 2>&1
    if [ -f /tmp/platepar_cmn2010.cal ] ; then 
        cfgfldr=$(dirname $RMSCFG)
        \cp -f $cfgfldr/platepar_cmn2010.cal $cfgfldr/platepar_cmn2010.cal.$(date +%Y%m%d-%H%M%S)
        \mv -f /tmp/platepar_cmn2010.cal $cfgfldr/
    fi 
    chmod 0600 live.key
    if [ -f archive.key ] ; then \rm archive.key ; fi
    echo "testing connections"
    source $here/ukmon.ini
    source ~/vRMS/bin/activate
    python $here/sendToLive.py test test
    python $here/uploadToArchive.py test
    echo "if you did not see two success messages contact us for advice" 
    read -p "Press any key to continue"
else
    echo "Location missing - please update UKMON Config File using the desktop icon"
    sleep 5
    read -p "Press any key to continue"
    exit 1
fi

# check and update the external script settings and crontab 
source $here/ukmon.ini
cd $(dirname $RMSCFG)
export PYTHONPATH=$here
python -c "import ukmonPostProc as pp ; pp.installUkmonFeed('${RMSCFG}');"

echo "done"
