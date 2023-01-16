import time
import os
import sys
import glob
import boto3
import sendToLive as uoe
import datetime
import logging
from RMS.Logger import initLogging
import RMS.ConfigReader as cr

log = logging.getLogger("logger")

timetowait = 30 # seconds to wait for a new line before deciding the log is stale
FBINTERVAL = int(os.getenv('FBINTERVAL', default='1800'))

def follow(fname):
    now = datetime.datetime.now().strftime('%Y/%m/%d %H:%M:%S')
    log.info('monitoring {}'.format(fname))
    thefile = open(fname, 'r')
    #thefile.seek(0, os.SEEK_START)
    
    t = 0
    while True:
        line = thefile.readline()
        if not line:
            time.sleep(0.1)
            t = t + 0.1
            if t > timetowait:
                t = 0
                yield('log stale')
                break
            else:
                continue
        else:
            t = 0
            yield(line.strip())


def monitorLogFile(camloc, rmscfg):
    """ Monitor the latest RMS log file for meteor detections, convert the FF file
    to a jpg and upload it to ukmon-live. Requires the user to have been supplied
    with a ukmon-live security key and camera location identifier. 
    """
    cfg = cr.parse(os.path.expanduser(rmscfg))

    
    log = logging.getLogger("logger")
    while len(log.handlers) > 0:
        log.removeHandler(log.handlers[0])
        
    initLogging(cfg, 'ukmonlive_')
    log.info('--------------------------------')
    log.info('    ukmon-live feed started')
    log.info('--------------------------------')

    log.info('Camera location is {}'.format(camloc))
    log.info('RMS config file is {}'.format(rmscfg))

    myloc = os.path.split(os.path.abspath(__file__))[0]

    awskey = None
    awssec = None
    awsreg = None

    # get credentials
    if not os.path.isfile(os.path.join(myloc, 'live.key')):
        log.info('AWS key not present, aborting')
        exit(1)
    with open(os.path.join(myloc, 'live.key'), 'r') as inif:
        lines = inif.readlines()
        for li in lines:
            if 'AWS_ACCESS_KEY_ID' in li:
                awskey = li.split('=')[1].strip()
            if 'AWS_SECRET_ACCESS_KEY' in li:
                awssec = li.split('=')[1].strip()
            if 'AWS_DEFAULT_REGION' in li:
                awsreg = li.split('=')[1].strip()
    if awssec is None or awskey is None or awsreg is None:
        log.info('unable to locate AWS credentials, aborting')
        exit(1)

    conn = boto3.Session(aws_access_key_id=awskey, aws_secret_access_key=awssec, region_name=awsreg) 
    s3 = conn.resource('s3')

    # read a few variables from the RMS config file
    loc = []
    loc.append(float(cfg.latitude))
    loc.append(float(cfg.longitude))
    loc.append(float(cfg.elevation))
    loc.append(cfg.stationID)
    loc.append(camloc)

    datadir = cfg.data_dir
    logdir = os.path.expanduser(os.path.join(datadir, cfg.log_dir))
    logfs = glob.glob1(logdir, 'log*.log*')
    logfs.sort()
    logf = os.path.join(logdir, logfs[-1])
    prevlogf = logf

    keepon = True
    starttime = datetime.datetime.now()
    startday = starttime.day
    while keepon is True:
        try:
            lis = open(logf,'r').readlines()
            dd = [li for li in lis if 'Data directory' in li]
            if len(dd) > 0:
                capdir = dd[0].split(' ')[5].strip()
                log.info('Capture dir is {}'.format(capdir))
            loglines = follow(logf)

            # iterate over the generator
            for line in loglines:
                if li == 'log stale':
                    log.info('file not being updated')
                    logfs = glob.glob1(logdir, 'log*.log*')
                    logfs.sort()
                    logf = os.path.join(logdir, logfs[-1])
                    if logf != prevlogf:
                        prevlogf = logf
                        loglines.close()
                else:
                    if "Data directory" in line: 
                        capdir = line.split(' ')[5].strip()
                        log.info('Capdir is', capdir)
                    if "detected meteors" in line and ": 0" not in line and "TOTAL" not in line:
                        if capdir != '':
                            ffname = line.split(' ')[3]
                            log.info('uploading {}'.format(ffname))
                            uoe.uploadOneEvent(capdir, ffname, loc, s3)
                nowtm = datetime.datetime.now()
                if nowtm.day != startday: 
                    log.info('rolling the logfile after midnight')
                    while len(log.handlers) > 0:
                        log.removeHandler(log.handlers[0])
                        
                    initLogging(cfg, 'ukmonlive_')
                    log.info('--------------------------------')
                    log.info('    ukmon-live feed started')
                    log.info('--------------------------------')

                    log.info('Camera location is {}'.format(camloc))
                    log.info('RMS config file is {}'.format(rmscfg))
                    starttime = nowtm
                    startday = starttime.day
                if (nowtm - starttime).seconds > FBINTERVAL:
                    try:
                        uoe.checkFbUpload(cfg.stationID, capdir, log)
                    except: 
                        print('problem checking fireball flags')
                    starttime = nowtm
        except StopIteration:
            log.info('restarting to read {}'.format(logf))
            pass


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('LOCATION missing')
        exit(1)
    if len(sys.argv) < 3:
        rmscfg = '/home/pi/source/RMS/.config'
    else:
        rmscfg = sys.argv[2]
    camloc = sys.argv[1]
    monitorLogFile(camloc, rmscfg)
