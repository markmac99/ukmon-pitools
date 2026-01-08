#!/bin/bash

#
# monitors the latest RMS log for potential meteors
# Copyright (C) 2018-2023 Mark McIntyre
#
source ~/vRMS/bin/activate
here="$( cd "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"

# kill any existing livestream process
pids=$(ps -ef | grep ${here}/liveMonitor | egrep -v "grep|$$" | awk '{print $2}')
[ "$pids" != "" ] && kill -9 $pids

source $here/ukmon.ini

cd ~/source/RMS
export PYTHONPATH=$here:~/source/RMS
if [ -f $here/cameras.ini ] ; then
    cat $here/cameras.ini | grep = | while read i 
    do 
        python $here/liveMonitor.py ${i:7:60} ${i:0:6} &
    done    
else
    if [ "$LOCATION" == "NOTCONFIGURED" ]; then
        echo "station not configured, unable to continue" 
        exit 1
    fi
    python $here/liveMonitor.py $LOCATION &
fi
