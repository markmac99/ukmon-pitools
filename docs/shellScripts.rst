Shell Scripts 
=============
There are two scripts, one to monitor the live datastream and send files to ukmon-live, the other to 
refresh the toolset each night and make sure the security keys are up to date.  A few other files are 
either created or installed, these are described below. 

**liveMonitor.sh**
    Shell script started from cron that runs the python script. 
    To use this add a line to cron:

    @boot sleep 3600 && /path/to/liveMonitor.sh > /home/pi/RMS_data/logs/ukmon-live.log 2>&1

**refreshTools.sh**
    Shell script that refreshes the toolset and downloads any keyfile changes
    To use this add a line to cron:

    @boot sleep 600 && /path/to/refreshTools.sh > /home/pi/RMS_data/logs/refreshTools.log 2>&1

**ukmon.ini live.key and archive.key**
Configuration and security key files required for the operation of the module. The ini file 
will be sent to you if you decide to become a UKMON member. The keys will then be automatically
downloaded when the refreshTools script is run.

**domp4s**
If this file exists, the script will additionally create an MP4 of each detection and 
upload it to the ukmon Archive each night.

**dotimelapse**
If this file exists, the script will additionally create an all-night timelapse. This is 
not uploaded, but you can share it on social media etc.

**extrascript**
If this file exists, ukmonPostProc will assume it is the full path to an additional script to 
run after all other processing is complete. The extra script is passed the same three arguments
as the normal RMS PostProcessing script. 

This is particularly useful if you also want to contribute to IstraStream. If you want to do this,
create the extrascript file containing one line:

*/home/pi/source/RMS/iStream/iStream.py*