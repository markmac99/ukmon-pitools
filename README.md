# ukmon-pitools
ukmeteornetwork toolset for RMS pi meteor cameras
=================================================

These tools manage uploads of RMS data to the UK Meteor Network Archive and Livestream.
To contribute your data, login to your pi and then type  
> cd ~/source  
> git clone https://github.com/markmac99/ukmon-pitools.git  

Then contact  ukmeteornetwork@gmail.com. We will add your ssh public key to our server, 
create security keys for you and send you a small config file.  

ukmonPostProc.py
================
Creates JPGs and other data, then uploads it to the UK Meteor Network archive. 
To use this script, set the following values in the RMS configuration file:

> external_script_run: true  
> auto_reprocess_external_script_run: true  
> auto_reprocess: true  
> external_script_path: /home/pi/source/ukmon-pitools/ukmonPostProc.py  

MP4s and Timelapse
------------------
The script can also create MP4s of each detection and a timelapse of the  whole night. 
To enable these, create files named "domp4s" or "dotimelapse" in the same folder as the script. eg:  
> echo "1" > /home/pi/source/ukmon-pitools/domp4s  
> echo "1" > /home/pi/source/ukmon-pitools/dotimelapse  

Running an Additional Script
----------------------------
If you want to run an additional script after this one finishes, create a file named "extrascript" in the same folder, containing a single line with the full path to the script, eg
> echo "/home/pi/myfolder/myscript.py" > /home/pi/source/ukmon-pitools/extrascript  

This script will be passed the capture_dir, archive_dir and RMS config object. 

uploadToArchive.py
==================
handles uploading to the UK meteor network archive. Can be called standalone if you want to reupload data:
eg  
> python uploadToArchive.py UK0006_20210312_183741_206154  

this will upload from /home/pi/RMS_data/ArchivedFiles/UK0006_20210312_183741_206154

refreshTools.sh
===============
Updates the UKMON RMS Toolset to the latest version. If we built your camera, this will run automatically
every time your Pi reboots. You can also run it manually. 

A good crontab entry would look like this (all on one line in the crontab)  
> @reboot sleep 60 && /home/pi/source/ukmon-pitools/refreshTools.sh > /home/pi/RMS_data/logs/refreshTools.log 2>&1  

refreshTools reads from a configuration file that is specific to your camera. We will send
you this file when you onboard to the network. The file contains your location ID and the
details of our sftp server used to distribute security keys. 
