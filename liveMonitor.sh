#!/bin/bash

#
# monitors the latest RMS log for potential meteors
#
source ~/vRMS/bin/activate
here="$( cd "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"

# kill any existing ukmon-live process
pids=$(ps -ef | grep ${here}/liveMonitor | egrep -v "grep|$$" | awk '{print $2}')
kill -9 $pids

source $here/ukmon.ini
source $here/live.key

if [ "$LOCATION" == "NOTCONFIGURED" ]; then
    echo "station not configured, unable to continue" 
    exit 1
fi

rmsdir=$(dirname $RMSCFG)
cd $rmsdir
export PYTHONPATH=$here:~/source/RMS
python $here/liveMonitor.py $LOCATION $RMSCFG 
