import time
import os
import sys
import glob
import boto3
import configparser
import sendToLive as uoe


def follow(thefile):
    # internal Generator function that yields new lines in a file

    # seek the end of the file
    thefile.seek(0, os.SEEK_END)
    
    # start infinite loop
    while True:
        # read last line of file
        line = thefile.readline()
        # sleep if file hasn't been updated
        if not line:
            time.sleep(0.1)
            continue
            
        yield line 


def monitorLogFile():
    """ Monitor the latest RMS log file for meteor detections, convert the FF file
    to a jpg and upload it to ukmon-live. Requires the user to have been supplied
    with a ukmon-live security key and camera location identifier. 
    """
    capdir = ''

    awskey = None
    awssec = None
    awsreg = None
    myloc = os.path.split(os.path.abspath(__file__))[0]

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

    # get cam location from ini file
    camloc = None
    rmsloc = '~/source/RMS/.config'
    with open(os.path.join(myloc, 'ukmon.ini'), 'r') as inif:
        lines = inif.readlines()
        for li in lines:
            if 'LOCATION' in li:
                camloc = li.split('=')[1].strip()
                break
            if 'RMSCFG' in li:
                rmsloc = li.split('=')[1].strip()
    if camloc is None or rmsloc is None:
        print('ini file malformed - LOCATION or RMSCFG not found')
        exit(1)


    # read a few variables from the RMS config file
    cfg = configparser.ConfigParser()
    cfg.read(os.path.expanduser(rmsloc))
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
    print('monitoring {}'.format(logf))

    logfile = open(logf, 'r')
    # determine data directory
    while True:
        line = logfile.readline()
        if not line: 
            break
        if "Data directory" in line: 
            capdir = line.split(' ')[5].strip()
            print('capdir is', capdir)
            sys.stdout.flush()
            break

    # rewind to start
    logfile.seek(0, 0)
    loglines = follow(logfile)

    # iterate over the generator
    for line in loglines:
        if "Data directory" in line: 
            capdir = line.split(' ')[5].strip()
            print('capdir is', capdir)
            sys.stdout.flush()

        if "detected meteors" in line and ": 0" not in line and "TOTAL" not in line:
            if capdir != '':
                ffname = line.split(' ')[3]
                uoe.uploadOneEvent(capdir, ffname, loc, s3)


if __name__ == '__main__':
    monitorLogFile()
