# ukmeteornetwork toolset for RMS pi meteor cameras

These tools manage uploads of RMS data to the UK Meteor Network Archive and Live-stream.

There is more information about RMS and the toolset in the wiki [here](https://github.com/markmac99/ukmon-pitools/wiki "UKMON Wiki")

## INSTALLATION

### Single Station / Pi installation
These instructions are for single-station setups such as on a Raspberry Pi.

* Login to your pi using VNC or AnyDesk or TeamViewer, open a Terminal window from the Accessories menu, then type the following
> cd $HOME/source  
> git clone https://github.com/markmac99/ukmon-pitools.git  
> cd ukmon-pitools  
> ./refreshTools.sh  

* When prompted, copy the SSH public key. 

* Email the key to markmcintyre99@googlemail.com along with your location (eg the name of your town or village) and the rough direction your camera points in eg SW, S, NE. The location should be no more than 16 characters. We will also need your camera ID, latitude, longitude and elevation from the RMS config file so that your data can be included in the Orbit and Trajectory solving routines. 

* We will add your key to our server and send you instructions for how to complete the setup.  

### Multistation Installation
These instructions are for multi station linux builds where multiple cameras are managed from a single
userid. 
NB: If you're setting up such a configuration you MUST let me know the affected camera IDs so i can make some server-side adjustments. Otherwise the ukmon ini file will be overwritten each time the system updates. 

To explain the process, lets assume you have cameras US0001 and US0002
* Login as the managing user and run the following to set up US0001
> cd $HOME/source
> git clone https://github.com/markmac99/ukmon-pitools.git  ukmon-pitools-US0001  
> cd ukmon-pitools-US0001  
> ./refreshTools.sh  

* This will create a default ukmon.ini file. Edit this file and make the following changes:
> export UKMONKEY=\~/.ssh/ukmon-US0001  
> export RMSCFG=\~/source/Stations/US0001/.config  

* Now rerun ./refreshTools.sh. This time it will create an SSH key called ~/.ssh/ukmon-US0001. 
 
* If you're setting up from scratch then email the public key to markmcintyre99@googlemail.com. We'll email back instructions in how to complete the process. 
  
* If you're migrating an existing installation from a pi, then you can copy over the existing keys as follows (replace 'yourpiname' with your Pi's network name or ip address):
> scp yourpiname:.ssh/ukmon \~/.ssh/ukmon-US0001  
> scp yourpiname:.ssh/ukmon.pub \~/.ssh/ukmon-US0001.pub  

* Now edit the ini file again and set the LOCATION to the correct value. 
* Then rerun ./refreshTools.sh. 
* This time, it should complete successfully. 

* If you have more than one camera, repeat these instructions for each camera

HOW THE TOOLS WORK
==================
ukmonPostProc.py
================
This uses the RMS post-processing hook to creates JPGs and other data, then upload to the UK Meteor Network archive. The script has three optional capabilities: 


MP4s and Timelapse
------------------
The script can  create MP4s of each detection and a timelapse of the  whole night. 
To enable these, create files named "domp4s" or "dotimelapse" in the same folder as the script:  
> echo "1" > $HOME/source/ukmon-pitools/domp4s  
> echo "1" > $HOME/source/ukmon-pitools/dotimelapse  

Running an Additional Script such as the Istrastream feed
---------------------------------------------------------
If you want to run an additional Python script after this one finishes, create a file named "extrascript"  in the same folder, containing a single line with the full path to the script, For example to enable the feed to istrastream, you could open a Terminal window and type the following:  
> echo "$HOME/source/RMS/iStream/iStream.py" > $HOME/source/ukmon-pitools/extrascript  

This script will be passed the capture_dir, archive_dir and RMS config object in the same way as RMS passes these to any external script. 

Note that before enabling a feed to Istrastream you must email info@istrastream.com with your camera ID, location and lens focal length. They'll enable your uploads and let you know. You'll get back instructions for how to enable iStream but please follow the above notes instead. 

uploadToArchive.py
==================
This does the actual  uploading to the UK meteor network archive. Can be called standalone if you want to reupload data:
eg  
> python uploadToArchive.py UK0006_20210312_183741_206154  

this will upload from $HOME/RMS_data/ArchivedFiles/UK0006_20210312_183741_206154

liveMonitor.sh
==============
This script monitors in realtime for detections, then uploads them to ukmon-live. The script calls a 
python script liveMonitor.py. 

sendToLive.py
-------------
Part of liveMonitor, this python script does the actual uploading. You can use it manually as follows:  
> python sendToLive.py capture-dir ff-file-name 

refreshTools.sh
===============
Updates the UKMON RMS Toolset to the latest version. After first run, this will run automatically
every time your Pi reboots. You can also run it manually. 

refreshTools reads from a configuration file that is specific to your camera. We will send
you this file when you onboard to the network. The file contains your location ID and the
details of our sftp server used to distribute security keys. 

Questions
=========
Any questions, concerns or suggestions:
* Check the wiki here https://github.com/markmac99/ukmon-pitools/wiki
* Join our group on Groups.io https://groups.io/g/ukmeteornetwork/topics
* As a last resort, email me via markmcintyre99@googlemail.com  

Copyright
=========
All code Copyright (C) 2018-2023 Mark McIntyre