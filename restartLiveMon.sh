#!/bin/bash

# this script can be used to restart the ukmon livefeed
# if it is killed. 
# just add this to your crontab:
# */10 * * * * /home/pi/source/ukmon-pitools/restartLiveMon.sh >/dev/null 2>&1
x=$(ps -ef | grep liveMon |wc -l)
if [ $x -lt 2 ] 
then 
    /home/pi/source/ukmon-pitools/liveMonitor.sh >> /home/pi/RMS_data/logs/ukmon-live.log 2>&1 &
fi