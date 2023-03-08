#!/bin/bash

#
# monitors the latest RMS log for potential meteors
# Copyright (C) 2018-2023 Mark McIntyre
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

# override this to change fireball check frequency. Zero means dont check at all
# export UKMFBINTERVAL=1800
# override this to allow reupload of older data. Files older than this many seconds will be ignored
# export UKMMAXAGE=1800

rmsdir=$(dirname $RMSCFG)
cd $rmsdir
export PYTHONPATH=$here:~/source/RMS
python $here/liveMonitor.py $LOCATION $RMSCFG 
