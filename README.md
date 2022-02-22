ukmeteornetwork toolset for RMS pi meteor cameras
=================================================
These tools manage uploads of RMS data to the UK Meteor Network Archive and Live-stream.

There is more information about RMS and the toolset in the wiki [here](https://github.com/markmac99/ukmon-pitools/wiki "UKMON Wiki")

INSTALLATION
------------
* Login to your pi using VNC or AnyDesk or TeamViewer, open a Terminal window from the Accessories menu, then type the following
> cd /home/pi/source  
> git clone https://github.com/markmac99/ukmon-pitools.git  
> cd ukmon-pitools  
> ./refreshTools.sh  

* When prompted, copy the SSH public key. 

* Email the key to markmcintyre99@googlemail.com along with your location (eg the name of your town or village) and the rough direction your camera points in eg SW, S, NE. The location should be no more than 16 characters. We will also need your camera ID, latitude, longitude and elevation from the RMS config file so that your data can be included in the Orbit and Trajectory solving routines. 

* We will add your key to our server and send you a small config file.  Copy this file into */home/pi/source/ukmon-pitools* 
* Once you've installed the ini file, re-run the *refreshTools.sh* script to download your security keys and bring the tools up to date. Answer 'yes' when prompted to accept the security key. 

* The refresh process will also update the RMS config file so that it runs the UKMON uploader process after each night's data capture finishes. If you already had a post-processing script configured, such as Istrastream, this will be preserved and will run after the UKMON job. The original config file is backed up to the ukmon-pitools folder. 


HOW THE TOOLS WORK
==================
ukmonPostProc.py
================
This uses the RMS post-processing hook to creates JPGs and other data, then upload to the UK Meteor Network archive. The script has three optional capabilities: 


MP4s and Timelapse
------------------
The script can  create MP4s of each detection and a timelapse of the  whole night. 
To enable these, create files named "domp4s" or "dotimelapse" in the same folder as the script:  
> echo "1" > /home/pi/source/ukmon-pitools/domp4s  
> echo "1" > /home/pi/source/ukmon-pitools/dotimelapse  

Running an Additional Script such as the Istrastream feed
---------------------------------------------------------
If you want to run an additional Python script after this one finishes, create a file named "extrascript"  in the same folder, containing a single line with the full path to the script, For example to enable the feed to istrastream, you could open a Terminal window and type the following:  
> echo "/home/pi/source/RMS/iStream/iStream.py" > /home/pi/source/ukmon-pitools/extrascript  

This script will be passed the capture_dir, archive_dir and RMS config object in the same way as RMS passes these to any external script. 

Note that before enabling a feed to Istrastream you must email info@istrastream.com with your camera ID, location and lens focal length. They'll enable your uploads and let you know. You'll get back instructions for how to enable iStream but please follow the above notes instead. 

uploadToArchive.py
==================
This does the actual  uploading to the UK meteor network archive. Can be called standalone if you want to reupload data:
eg  
> python uploadToArchive.py UK0006_20210312_183741_206154  

this will upload from /home/pi/RMS_data/ArchivedFiles/UK0006_20210312_183741_206154

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
