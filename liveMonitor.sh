#!/bin/bash

#
# monitors the latest RMS log for potential meteors
#
source ~/vRMS/bin/activate
here="$( cd "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
source $here/ukmon.ini
source $here/live.key

if [ "$LOCATION" == "NOTCONFIGURED" ]; then
    echo "station not configured, unable to continue" 
    exit 1
fi

rmsdir=$(dirname $RMSCFG)
cd $rmsdir
export PYTHONPATH=$here:~/source/RMS
logger -s -t ukmonLiveMonitor "starting"
logger -s -t ukmonLiveMonitor "=========="
python $here/liveMonitor.py $LOCATION $RMSCFG 
