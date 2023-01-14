import time
import os
import sys
import glob
import boto3
import configparser
import sendToLive as uoe
import datetime

timetowait = 30 # seconds to wait for a new line before deciding the log is stale


def follow(fname):
    now = datetime.datetime.now().strftime('%Y/%m/%d %H:%M:%S')
    print('{}: monitoring {}'.format(now, fname))
    thefile = open(fname, 'r')
    #thefile.seek(0, os.SEEK_START)
    
    t = 0
    while True:
        line = thefile.readline()
        if not line:
            time.sleep(0.1)
            t = t + 0.1
            print(t)
            if t > timetowait:
                yield('log stale')
            continue
        else:
            t = 0
            yield(line.strip())


def monitorLogFile(camloc, rmscfg):
    """ Monitor the latest RMS log file for meteor detections, convert the FF file
    to a jpg and upload it to ukmon-live. Requires the user to have been supplied
    with a ukmon-live security key and camera location identifier. 
    """
    print('Camera location is {}'.format(camloc))
    print('RMS config file is {}'.format(rmscfg))
    myloc = os.path.split(os.path.abspath(__file__))[0]

    awskey = None
    awssec = None
    awsreg = None

    # get credentials
    if not os.path.isfile(os.path.join(myloc, 'live.key')):
        print('AWS key not present, aborting')
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
        print('unable to locate AWS credentials, aborting')
        exit(1)

    conn = boto3.Session(aws_access_key_id=awskey, aws_secret_access_key=awssec, region_name=awsreg) 
    s3 = conn.resource('s3')

    # read a few variables from the RMS config file
    cfg = configparser.ConfigParser()
    cfg.read(os.path.expanduser(rmscfg))
    loc = []
    loc.append(float(cfg['System']['latitude'].split()[0]))
    loc.append(float(cfg['System']['longitude'].split()[0]))
    loc.append(float(cfg['System']['elevation'].split()[0]))
    loc.append(cfg['System']['stationID'].split()[0])
    loc.append(camloc)

    datadir = cfg['Capture']['data_dir']
    logdir = os.path.expanduser(os.path.join(datadir, cfg['Capture']['log_dir']))
    logfs = glob.glob1(logdir, 'log*.log*')
    logfs.sort()
    logf = os.path.join(logdir, logfs[-1])

    keepon = True
    while keepon is True:
        try:
            loglines = follow(logf)

            # iterate over the generator
            for line in loglines:
                if li == 'log stale':
                    print('file not being updated')
                    logfs = glob.glob1(logdir, 'log*.log*')
                    logfs.sort()
                    logf = os.path.join(logdir, logfs[-1])
                    loglines.close()
                else:
                    if "Data directory" in line: 
                        capdir = line.split(' ')[5].strip()
                        print('Capdir is', capdir)
                        sys.stdout.flush()
                    if "detected meteors" in line and ": 0" not in line and "TOTAL" not in line:
                        if capdir != '':
                            ffname = line.split(' ')[3]
                            uoe.uploadOneEvent(capdir, ffname, loc, s3)
        except:
            print('restarting to read {}'.format(logf))
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
