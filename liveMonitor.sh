#!/bin/bash

#
# monitors the latest RMS log for potential meteors
#
source ~/vRMS/bin/activate
here="$( cd "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
source $here/ukmon.ini
source $here/live.key

logf=`ls -1tr ~/RMS_data/logs/log*.log | tail -1 | head -1`
logger "Monitoring $logf" -t $0

cd ~/source/RMS

python $here/liveMonitor.py $logf
