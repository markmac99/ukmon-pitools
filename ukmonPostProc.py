# 
# python script thats called when the nightly run completes to generate jpgs 
# and upload data to the uk meteor data archive
# Copyright (C) 2018-2023 Mark McIntyre
#
# Notes: 
# - to enable MP4 creation of each detection, create a file 'domp4s' in the same folder as this script
# - to enable creation of an all-night timelapse, create a file 'dotimelapse'
# - to trigger another python script after this one, create a file 'extrascript' containing the full path 
#   to the extra script. The script will be passed the same arguments as this one (cap_dir, arc_dir, config)

import os
import sys
import glob
import time

import Utils.BatchFFtoImage as bff2i
import Utils.GenerateMP4s as gmp4
import RMS.ConfigReader as cr
from importlib import import_module as impmod
import logging
import datetime

from uploadToArchive import uploadToArchive, readIniFile


log = logging.getLogger("ukmonlogger")
log.setLevel(logging.INFO)

versionid = '2026.01.04'


def setupLogging(logpath, prefix):
    print('about to initialise logger')
    logdir = os.path.expanduser(logpath)
    os.makedirs(logdir, exist_ok=True)
    log.info('removing any existing log handlers')
    for handler in log.handlers[:]:
        log.removeHandler(handler)

    logfilename = os.path.join(logdir, prefix + datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d_%H%M%S.%f') + '.log')
    handler = logging.handlers.TimedRotatingFileHandler(logfilename, when='D', interval=1) 
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter(fmt='%(asctime)s-%(levelname)s-%(module)s-line:%(lineno)d - %(message)s', 
        datefmt='%Y/%m/%d %H:%M:%S')
    handler.setFormatter(formatter)
    log.addHandler(handler)

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.WARNING)
    formatter = logging.Formatter(fmt='%(asctime)s-%(levelname)s-%(module)s-line:%(lineno)d - %(message)s', 
        datefmt='%Y/%m/%d %H:%M:%S')
    ch.setFormatter(formatter)
    log.addHandler(ch)

    log.setLevel(logging.INFO)

    purgeOldLogs(logdir, prefix)

    log.info('logging initialised')
    return 


def purgeOldLogs(logdir, logpref, days=30):
    reftime = time.time() - 86400*days
    for logf in glob.glob(os.path.join(logdir, logpref + '*.log*')):
        if os.path.getmtime(logf) < reftime:
            log.debug('removing old log', logf)
            os.remove(logf)
    return 


def rmsExternal(cap_dir, arch_dir, config):
    """ Called from RMS to trigger the UKMON specific code  

    Args:  
        cap_dir (str): full path to the night's CapturedFiles folder  
        arch_dir (str): full path to the night's ArchivedFiles folder  
        config (object): an RMS config object.  

    Don't try to call this function directly unless you know how to create
    an RMS config object in Python. 

    """
    setupLogging(os.path.join(config.data_dir, config.log_dir), f'ukmon_log_{config.stationID}_')
    log.info('ukmon external script started, version ' + versionid)
    
    rebootlockfile = os.path.join(config.data_dir, config.reboot_lock_file)
    with open(rebootlockfile, 'w') as f:
        f.write('1')

    log.info('uploading key science files to archive')
    keys = uploadToArchive(arch_dir, config.stationID, sciencefiles=True)
    # create jpgs from the potential detections
    log.info('creating JPGs')
    try:
        bff2i.batchFFtoImage(arch_dir, 'jpg', True)
    except Exception:
        bff2i.batchFFtoImage(arch_dir, 'jpg')

    myloc = os.path.split(os.path.abspath(__file__))[0]
    inifvals = readIniFile(os.path.join(myloc, 'ukmon.ini'), config.stationID)
    if not inifvals or inifvals['LOCATION']=='NOTCONFIGURED':
        return False
    log.info('app home is {}'.format(myloc))
    domp4s = 0
    if 'DOMP4S' in inifvals:
        domp4s = int(inifvals['DOMP4S'])
    elif os.path.isfile(os.path.join(myloc, 'domp4s')):
        domp4s = 1
    if domp4s == 1: 
        # generate MP4s of detections
        log.info('generating MP4s')
        ftpdate=''
        if os.path.split(arch_dir)[1] == '':
            ftpdate=os.path.split(os.path.split(arch_dir)[0])[1]
        else:
            ftpdate=os.path.split(arch_dir)[1]
        ftpfile_name="FTPdetectinfo_"+ftpdate+'.txt'
        try:
            maglim = 1
            if 'MAGLIM' in inifvals:
                maglim = float(inifvals['MAGLIM'])
            gmp4.generateMP4s(arch_dir, ftpfile_name, min_mag=maglim)
        except Exception:
            gmp4.generateMP4s(arch_dir, ftpfile_name)
    else:
        log.info('mp4 creation not enabled')
    
    log.info('uploading remaining files to archive')
    uploadToArchive(arch_dir, config.stationID, keys=keys)

    # do not remove reboot lock file if running another script
    # os.remove(rebootlockfile)
    
    extrascrfn = os.path.join(myloc, 'extrascript')
    if os.path.isfile(extrascrfn):
        extrascript = open(extrascrfn,'r').readline().strip()
        log.info('running additional script {:s}'.format(extrascript))
        while len(log.handlers) > 0:
            log.removeHandler(log.handlers[0])  
        sloc, sname = os.path.split(extrascript)
        sys.path.append(sloc)
        scrname, _ = os.path.splitext(sname)
        nextscr=impmod(scrname)
        nextscr.rmsExternal(cap_dir, arch_dir, config)
    else:
        log.info('additional script not called')
        try:
            os.remove(rebootlockfile)
        except Exception:
            log.info('unable to remove reboot lock file, pi will not reboot')
            pass

    log.info('done')
    # clear log handlers again
    while len(log.handlers) > 0:
        log.removeHandler(log.handlers[0])  
    return True


def manualRerun(dated_dir, rmscfg = '~/source/RMS/.config'):
    """This function is used to manually rerun the Ukmon post processing script.  
    To invoke this function, open a Terminal window and run the following:  

    *python ../ukmon-pitools/ukmonPostProc.py dated_dir*  

    Args:
        dated_dir (str): The name of the folder to upload eg UK000F_20210512_202826_913898  

    """
    config = cr.parse(os.path.expanduser(rmscfg))
    cap_dir = os.path.join(config.data_dir, 'CapturedFiles', dated_dir)
    if not os.path.isdir(cap_dir):
        return False
    arch_dir = os.path.join(config.data_dir, 'ArchivedFiles', dated_dir)
    if not os.path.isdir(arch_dir):
        return False
    return rmsExternal(cap_dir, arch_dir, config)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('usage: python ukmonPostProc.py arc_dir_name')
        print('eg python ukmonPostProc.py UK0006_20210312_183741_206154')
        exit(0)
    
    arch_dir = sys.argv[1]
    if 'ConfirmedFiles' in arch_dir or 'ArchivedFiles' in arch_dir or 'CapturedFiles' in arch_dir:
        _, arch_dir = os.path.split(arch_dir)
    stationid = arch_dir.split('_')[0]
    myloc = os.path.split(os.path.abspath(__file__))[0]
    inifvals = readIniFile(os.path.join(myloc, 'ukmon.ini'), stationid)
    if not inifvals or inifvals['LOCATION']=='NOTCONFIGURED':
        print('ukmon ini file invalid - check LOCATION')
        exit(1)
    try:
        rmscfg = inifvals['RMSCFG']
    except Exception:
        rmscfg='~/source/RMS/.config'
    try:
        print('RMS config read from {}'.format(rmscfg))
        ret = manualRerun(arch_dir, rmscfg)
        exit(0)
    except Exception:
        print('unable to call manualRerun')
        exit(1)
