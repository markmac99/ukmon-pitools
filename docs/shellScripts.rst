Shell Scripts 
=============
There are two scripts, one to monitor the live datastream and send files to the livestream, the other to 
refresh the toolset each night and make sure the security keys are up to date.  A few other files are 
either created or installed, these are described below. 

**Note about hardware**
If you've installed on linux hardware instead of a Pi,  replace the username "pi" 
with the userid that you used when you installed RMS and ukmon-pitools. 

**liveMonitor.sh**
    Shell script started from cron that triggers the process to monitor and upload events to the 
    livestream on the website. The script runs a python monitoring process described elsewhere in the 
    documentation.To use this script add a line to crontab:

    *@boot sleep 3600 && /path/to/liveMonitor.sh > /dev/null 2>&1*

**refreshTools.sh**
    Shell script that refreshes the toolset and downloads any changes after each reboot. Its 
    important that this is scheduled to run every day as the keyfiles are periodically rotated
    and bugfixes and enhancements deployed through this script. To use this script add a line to crontab:

    *@boot sleep 600 && /path/to/refreshTools.sh > /home/pi/RMS_data/logs/refreshTools.log 2>&1*

Other files
-----------
These files are either created automatically by the refresh script, or can be created by the 
user to enable extra features of the process. 

**ukmon.ini and live.key**
Configuration files required for the operation of the module. A default ini file 
is deployed from github and you'll be given instructions on how to update it. 
The other file will be automatically downloaded when the refreshTools script is run.

**domp4s**
If this file exists, the script will additionally create an MP4 of each detection and 
upload it to the ukmon Archive each night.

**extrascript**
If this file exists, ukmonPostProc will assume it is the full path to an additional script to 
run after all other processing is complete. The extra script is passed the same three arguments
as the normal RMS PostProcessing script. 
