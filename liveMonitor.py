import time
import os
import sys
import boto3
import configparser
import sendToLive as uoe


def follow(thefile):
    '''generator function that yields new lines in a file
    '''
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


if __name__ == '__main__':
    
    capdir = ''

    awskey = None
    awssec = None
    awsreg = None
    myloc = os.path.split(os.path.abspath(__file__))[0]

    # get credentials
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
    logfile = open(sys.argv[1],"r")

    # get cam location from ini file
    camloc = None
    with open(os.path.join(myloc, 'ukmon.ini'), 'r') as inif:
        lines = inif.readlines()
        for li in lines:
            if 'LOCATION' in li:
                camloc = li.split('=')[1].strip()
                break
    if camloc is None:
        print('ini file malformed - LOCATION not found')
        exit(1)


    # read a few variables from the RMS config file
    cfg = configparser.ConfigParser()
    cfg.read('/home/pi/source/RMS/.config')
    loc = []
    loc.append(float(cfg['System']['latitude'].split()[0]))
    loc.append(float(cfg['System']['longitude'].split()[0]))
    loc.append(float(cfg['System']['elevation'].split()[0]))
    loc.append(cfg['System']['stationID'].split()[0])
    loc.append(camloc)

    # determine data directory
    while True:
        line = logfile.readline()
        if not line: 
            break
        if "Data directory" in line: 
            capdir = line.split(' ')[5].strip()
            print('capdir is', capdir, flush=True)
            break

    # rewind to start
    logfile.seek(0, 0)
    loglines = follow(logfile)

    # iterate over the generator
    for line in loglines:
        if "Data directory" in line: 
            capdir = line.split(' ')[5].strip()
            print('capdir is', capdir, flush=True)

        if "detected meteors" in line and ": 0" not in line and "TOTAL" not in line:
            if capdir != '':
                ffname = line.split(' ')[3]
                uoe.uploadOneEvent(capdir, ffname, loc, s3)
