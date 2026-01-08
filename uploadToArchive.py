# 
# Upload to ukmon from Python
# Copyright (C) 2018-2023 Mark McIntyre
#
# to use this to manually upload call it thus
#
#   cd ~/source/RMS
#   python ../ukmon-pitools/uploadToArchive.py arcdir
#
# where archdir is the full path to the folder you want to upload

import boto3
import os
import sys
import json
import random
import glob
import logging
from time import sleep
import warnings
from cryptography.utils import CryptographyDeprecationWarning
with warnings.catch_warnings():
    warnings.filterwarnings('ignore', category=CryptographyDeprecationWarning)
    import paramiko
import tempfile
import configparser

from RMS.Formats.FTPdetectinfo import readFTPdetectinfo


log = logging.getLogger("ukmonlogger")
logging.getLogger("paramiko").setLevel(logging.WARNING)


def getLatestKeys(homedir, stationid, remoteinifname='ukmon.ini'):
    """
    Retrieve the latest ini and key files from the ukmon server.  
    If the ini file contains a new server IP or new location, the local copy of the 
    ini file is updated accordingly.  
    """
    homedir = os.path.expanduser(os.path.normpath(homedir))
    inifvals = readIniFile(os.path.join(homedir, 'ukmon.ini'), stationid)
    if not inifvals or inifvals['LOCATION']=='NOTCONFIGURED':
        return False
    if not os.path.isfile(os.path.expanduser(inifvals['UKMONKEY'])):
        return False
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    pkey = paramiko.RSAKey.from_private_key_file(os.path.expanduser(inifvals['UKMONKEY'])) 
    try:
        ssh_client.connect(inifvals['UKMONHELPER'], username=inifvals['LOCATION'], pkey=pkey, look_for_keys=False)
        ftp_client = ssh_client.open_sftp()
    except Exception:
        return False

    # get the aws key file
    ftp_client.get('live.key', os.path.join(homedir, 'live.key'))
    os.chmod(os.path.join(homedir, 'live.key'), 0o600)

    # get the new ini and check for changes
    currinif = os.path.join(homedir, 'ukmon.ini')
    newinif = os.path.join(homedir, '.ukmon.new')
    ftp_client.put(currinif,'ukmon.ini.client')
    ftp_client.get(remoteinifname, newinif)
    ftp_client.close()
    iniflines = open(newinif,'r').readlines()
    for li in iniflines:
        li = li.strip()
        if 'UKMONHELPER' in li:
            newhelper = li.split('=')[1]
            if newhelper != inifvals['UKMONHELPER']:
                updateHelperIp(homedir, newhelper)
                print('server address updated')
        if 'LOCATION' in li:
            newloc = li.split('=')[1]
            if newloc != inifvals['LOCATION']:
                updateLocation(homedir, newloc)
                print('location updated')
    os.remove(newinif)
    ssh_client.close()
    return True


def readKeyFile(filename, inifvals):
    if not os.path.isfile(filename):
        log.error('Keyfile {} not downloaded. Check ssh key and station location with ukmon team.'.format(filename))
        return False
    with open(filename, 'r') as fin:
        lis = fin.readlines()
    vals = {}
    for li in lis:
        if li[0]=='#':
            continue
        if 'ACCESS_KEY' in li: # ignore keys in the file
            continue
        if '=' in li:
            valstr = li.split(' ')[1]
            data = valstr.split('=')
            val = data[1].strip().strip('"')
            vals[data[0]] = val
    if 'S3FOLDER' not in vals and 'CAMLOC' in vals:
        vals['S3FOLDER'] = 'archive/{}'.format(vals["CAMLOC"])
    if 'S3FOLDER' in vals and vals['S3FOLDER'][-1] == '/':
        vals['S3FOLDER'] = vals['S3FOLDER'][:-1]
    if 'ARCHBUCKET' not in vals:
        vals['ARCHBUCKET'] = 'ukmda-shared'
    if 'LIVEBUCKET' not in vals:
        vals['LIVEBUCKET'] = 'ukmda-live'
    if 'WEBBUCKET' not in vals:
        vals['WEBBUCKET'] = 'ukmda-website'
    if 'ARCHREGION' not in vals:
        vals['ARCHREGION'] = 'eu-west-2'
    if 'LIVEREGION' not in vals:
        vals['LIVEREGION'] = 'eu-west-1'
    if 'MATCHDIR' not in vals:
        vals['MATCHDIR'] = 'matches/RMSCorrelate'
    retries = 20
    tries = 0
    keyid, secid = False, False
    while tries < retries:
        keyid, secid = getAWSKey(inifvals)
        if keyid:
            break
        tries += 1
        log.info('retrying... try {}'.format(tries))
        sleep(30)
    if not keyid:
        return False
    vals['AWS_ACCESS_KEY_ID'] = keyid
    vals['AWS_SECRET_ACCESS_KEY'] = secid
    return vals


def updateHelperIp(homedir, helperip):
    """
    Update the ukmon.ini file with a new IP address if neeeded. 
    """
    homedir = os.path.normpath(homedir)
    lis = open(os.path.join(homedir, 'ukmon.ini'), 'r').readlines()
    with open(os.path.join(homedir, 'ukmon.ini'), 'w') as outf:
        for li in lis:
            if 'UKMONHELPER' in li:
                outf.write("export UKMONHELPER={}\n".format(helperip))
            else:
                outf.write('{}'.format(li))
    return


def updateLocation(homedir, newloc):
    """
    Update the ukmon-specific location, if a new one was supplied. Allows us to move cameras to new sites. 
    """
    homedir = os.path.normpath(homedir)
    lis = open(os.path.join(homedir, 'ukmon.ini'), 'r').readlines()
    with open(os.path.join(homedir, 'ukmon.ini'), 'w') as outf:
        for li in lis:
            if 'LOCATION' in li:
                outf.write("export LOCATION={}\n".format(newloc))
            else:
                outf.write('{}'.format(li))
    return 


def getAWSKey(inifvals):
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    key, sec = False, False
    try: 
        pkey = paramiko.RSAKey.from_private_key_file(os.path.expanduser(inifvals['UKMONKEY']))
        ssh_client.connect(inifvals['UKMONHELPER'], username=inifvals['LOCATION'], pkey=pkey, look_for_keys=False)
        ftp_client = ssh_client.open_sftp()
        try:
            handle, tmpfnam = tempfile.mkstemp()
            ftp_client.get(inifvals['LOCATION']+'.csv', tmpfnam)
        except Exception as e:
            log.error('unable to find AWS key, check location in ukmon.ini')
            log.info(e, exc_info=True)
        ftp_client.close()
        try:
            lis = open(tmpfnam, 'r').readlines()
            os.close(handle)
            os.remove(tmpfnam)
            key, sec = lis[1].split(',')
        except Exception as e:
            log.error('malformed AWS key, contact support')
            log.info(e, exc_info=True)
    except Exception as e:
        log.error('unable to retrieve AWS key')
        log.info(e, exc_info=True)
    ssh_client.close()
    if key:
        return key.strip(), sec.strip() 
    else: 
        return False, False


def readIniFile(filename, stationid):
    myloc = os.path.dirname(filename)
    camerafile = os.path.join(myloc,'cameras.ini')
    if not os.path.isfile(camerafile):
        location = None
    else:
        stations = getListOfStations(myloc)
        thiscam = [x for x in stations if stationid.lower() in x[0]]
        if len(thiscam)==0:
            log.error('camera {} not in cameras.ini, cannot continue'.format(stationid))
            print('missing camera file')
            return None
        location = thiscam[0][1]
    if not os.path.isfile(filename):
        log.error('{} missing, cannot continue'.format(filename))
        print('missing file')
        return None
    lis = open(filename, 'r').readlines()
    vals = {}
    for li in lis:
        if li[0]=='#':
            continue
        if '=' in li:
            valstr = li.split(' ')[1]
            data = valstr.split('=')
            val = data[1].strip().strip('"')
            vals[data[0]] = val
    if location:
        vals['LOCATION'] = location.strip()
    if stationid:
        if os.path.isfile(os.path.expanduser('~/.ssh/ukmon_' + stationid.upper())):
            vals['UKMONKEY'] = '~/.ssh/ukmon_' + stationid.upper()
        if os.path.isfile(os.path.expanduser('~/source/Stations/' + stationid + '/.config')):
            vals['RMSCFG'] = os.path.expanduser('~/source/Stations/' + stationid + '/.config')
    #if vals['LOCATION'] == 'NOTCONFIGURED':
    #    return None
    return vals


def uploadOneFile(arch_dir, dir_file, s3, targf, file_ext, keys):
    if 'ukmon' in keys['ARCHBUCKET'] or 'ukmda' in keys['ARCHBUCKET']:
        sts = uploadOneFileUKMon(arch_dir, dir_file, s3, targf, file_ext, keys)
    else:
        sts = uploadOneFileOther(arch_dir, dir_file, s3, targf, file_ext, keys)
    return sts


def uploadOneFileOther(arch_dir, dir_file, s3, targf, file_ext, keys):
    target = keys['ARCHBUCKET']
    daydir = os.path.split(arch_dir)[1]
    spls = daydir.split('_')
    camid = spls[0]
    desf= '{}/{}/{}/{}'.format(targf, camid, daydir, dir_file)
    ctyp='text/plain'
    if file_ext=='.jpg': 
        ctyp = 'image/jpeg'
    elif file_ext=='.fits': 
        ctyp = 'image/fits'
    elif file_ext=='.png': 
        ctyp = 'image/png'
    elif file_ext=='.bmp': 
        ctyp = 'image/bmp'
    elif file_ext=='.mp4': 
        ctyp = 'video/mp4'
    elif file_ext=='.csv': 
        ctyp = 'text/csv'
    elif file_ext=='.json':
        ctyp = 'application/json'

    srcf = os.path.join(arch_dir, dir_file)
    try:
        s3.meta.client.upload_file(srcf, target, desf, ExtraArgs={'ContentType': ctyp})
        ret = True
        log.info(desf)
    except Exception:
        ret = False
        log.info('upload failed: {}'.format(desf))
    return ret


def uploadOneFileUKMon(arch_dir, dir_file, s3, targf, file_ext, keys):
    # upload a single file to ukmon, setting the mime type accordingly
    # targets:
    # - ff jpegs, mp4s, kmls -> website/img/
    # - kmls also to shared/kmls/
    # - ufo csv - shared/consolidated/temp/
    # - platepar.cal - shared/consolidated/platepars/
    # - config, platepars_all, ftpdetect -> shared/matches/RMSCorrelate/
    # - other pngs, flux json files, mask, flat and any fits files - shared/archive/
    # - config also to shared/archive/
    
    target = keys['ARCHBUCKET']
    target2 = None
    daydir = os.path.split(arch_dir)[1]
    spls = daydir.split('_')
    camid = spls[0]
    ymd = spls[1]
    #log.info(f'matchdir is {keys["MATCHDIR"]}, targf is {targf}')
    
    desf= '{}/{}/{}/{}/{}/{}'.format(targf, camid, ymd[:4], ymd[:6], ymd, dir_file)
    desf2 = None
    ctyp='text/plain'
    if file_ext=='.jpg': 
        ctyp = 'image/jpeg'
        if 'FF_' in dir_file:
            target=keys['WEBBUCKET']
            ispls = dir_file.split('_')
            iymd = ispls[2]
            desf = 'img/single/{}/{}/{}'.format(iymd[:4], iymd[:6], dir_file)
    elif file_ext=='.fits':        
        ctyp = 'image/fits'
    elif file_ext=='.png': 
        ctyp = 'image/png'
    elif file_ext=='.bmp': 
        ctyp = 'image/bmp'
    elif file_ext=='.mp4': 
        ctyp = 'video/mp4'
        if 'FF_' in dir_file:
            target=keys['WEBBUCKET']
            vspls = dir_file.split('_')
            vymd = vspls[2]
            desf = 'img/mp4/{}/{}/{}'.format(vymd[:4], vymd[:6], dir_file)
    elif file_ext=='.csv': 
        ctyp = 'text/csv'
        desf='consolidated/temp/{}'.format(dir_file)
    elif file_ext=='.cal': 
        ctyp = 'text/plain'
        desf='consolidated/platepars/{}.json'.format(camid)
    elif file_ext=='.json':
        ctyp = 'application/json'
        if 'platepars_all' in dir_file: 
            desf = '{}/{}/{}/{}'.format(keys["MATCHDIR"], camid, daydir, dir_file)
    elif dir_file == 'FTPdetectinfo_{}.txt'.format(daydir): 
        ctyp = 'text/plain'
        desf = '{}/{}/{}/{}'.format(keys["MATCHDIR"], camid, daydir, dir_file)
    elif file_ext == '.kml': 
        ctyp = 'text/plain'
        desf = 'kmls/{}'.format(dir_file)
        target2 = keys['WEBBUCKET']
        desf2 = 'img/kmls/{}'.format(dir_file)
    if dir_file == '.config':
        ctyp = 'text/plain'
        target2 = target
        desf2 = '{}/{}/{}/{}'.format(keys["MATCHDIR"], camid, daydir, dir_file)

    srcf = os.path.join(arch_dir, dir_file)
    if not os.path.isfile(srcf):
        srcf = srcf.replace('ArchivedFiles','CapturedFiles')
        if not os.path.isfile(srcf):
            log.info('File not found: {}'.format(srcf))
            return True
    try:
        s3.meta.client.upload_file(srcf, target, desf, ExtraArgs={'ContentType': ctyp})
        ret = True
        log.info(desf)
    except Exception:
        ret = False
        log.info('upload failed: {}'.format(desf))
    if desf2 is not None:
        try:
            s3.meta.client.upload_file(srcf, target2, desf2, ExtraArgs={'ContentType': ctyp})
            ret = True
            log.info(desf2)
        except Exception:
            ret = False
            log.info('upload failed: {}'.format(srcf))
    return ret


def checkMags(dir_path, ftpfile_name, min_mag):
    log.info('checking for events brighter than mag {}'.format(min_mag))
    ff_names = []
    try:
        meteor_list = readFTPdetectinfo(dir_path, ftpfile_name)  
    except Exception:
        log.info('FTPdetect file not present so unable to filter by magnitude')
        return ff_names
    for meteor in meteor_list:
        ff_name, _, meteor_no, n_segments, _, _, _, _, _, _, _, \
            meteor_meas = meteor
        # checks on mag and shower        
        best_mag = 999
        if min_mag is not None:
            for meas in meteor_meas:
                best_mag = min(best_mag, meas[9])
            if best_mag > min_mag:
                log.info('rejecting {} as {} too dim'.format(ff_name, best_mag))
                continue
            else:
                ff_names.append(ff_name.replace('.fits', '.jpg'))
    return ff_names


def uploadToArchive(arch_dir, stationid, sciencefiles=False, keys=False):
    # Upload all relevant files from *arch_dir* to ukmon's S3 Archive

    myloc = os.path.split(os.path.abspath(__file__))[0]
    inifvals = readIniFile(os.path.join(myloc, 'ukmon.ini'), stationid)
    if inifvals['LOCATION']=='NOTCONFIGURED':
        return False
    if not keys:
        keys = readKeyFile(os.path.join(myloc, 'live.key'), inifvals)
        if not keys:
            return False
    reg = keys['ARCHREGION']
    conn = boto3.Session(aws_access_key_id=keys['AWS_ACCESS_KEY_ID'], aws_secret_access_key=keys['AWS_SECRET_ACCESS_KEY']) 
    s3 = conn.resource('s3', region_name=reg)
    targf = keys['S3FOLDER']
    maglim = 10.0
    if 'MAGLIM' in inifvals:
        maglim = float(inifvals['MAGLIM'])

    # upload the files but make sure we do the platepars file before the FTP file
    # otherwise there's a risk the matching engine will miss it
    dir_contents = os.listdir(arch_dir)
    daydir = os.path.split(arch_dir)[1]

    validffs = checkMags(arch_dir, 'FTPdetectinfo_{}.txt'.format(daydir), maglim)

    uploadlist = []
    if sciencefiles:
        # upload just the critical files
        # platepar must be uploaded before FTPdetect and config files
        uploadlist.append({'dir_file':'platepars_all_recalibrated.json', 'file_ext': '.json', 'src_dir': arch_dir})
        uploadlist.append({'dir_file':'.config', 'file_ext': '.config', 'src_dir': arch_dir})
        ftpfiles = [x for x in dir_contents if 'FTPdetectinfo' in x]
        for dir_file in ftpfiles:
            if ('FTPdetectinfo_{}.txt'.format(daydir) == dir_file):
                uploadlist.append({'dir_file':dir_file, 'file_ext': '.txt', 'src_dir': arch_dir})
                break
    else:
        # upload everything
        for dir_file in dir_contents:
            file_name, file_ext = os.path.splitext(dir_file)
            file_ext = file_ext.lower()
            if 'platepars_all_recalibrated' in file_name:
                continue
            # mp4 must be uploaded before corresponding jpg
            elif (file_ext == '.jpg') and ('FF_' in file_name):
                if dir_file in validffs or validffs == []:
                    mp4f = dir_file.replace('.jpg', '.mp4')
                    if os.path.isfile(os.path.join(arch_dir, mp4f)):
                        uploadlist.append({'dir_file':mp4f, 'file_ext': '.mp4', 'src_dir': arch_dir})
                    uploadlist.append({'dir_file':dir_file, 'file_ext': file_ext, 'src_dir': arch_dir})
            elif (file_ext == '.jpg') and ('stack_' in file_name) and ('track' not in file_name):
                uploadlist.append({'dir_file':dir_file, 'file_ext': file_ext, 'src_dir': arch_dir})
            elif (file_ext == '.jpg') and ('calib' in file_name):
                uploadlist.append({'dir_file':dir_file, 'file_ext': file_ext, 'src_dir': arch_dir})
            elif file_ext in ('.png', '.kml', '.cal', '.json', '.csv'): 
                uploadlist.append({'dir_file':dir_file, 'file_ext': file_ext, 'src_dir': arch_dir})
            elif dir_file == 'mask.bmp' or dir_file == 'flat.bmp':
                uploadlist.append({'dir_file':dir_file, 'file_ext': file_ext, 'src_dir': arch_dir})
        
        # upload two FITs files chosen at random from the recalibrated ones
        # to be used for platepar creation if needed
        if os.path.isfile(os.path.join(arch_dir, 'platepars_all_recalibrated.json')):
            with open(os.path.join(arch_dir, 'platepars_all_recalibrated.json')) as ppf:
                js = json.load(ppf)
            try:
                ffs=[k for k in js.keys() if js[k]['auto_recalibrated'] is True]
            except Exception:
                ffs = glob.glob1(arch_dir, 'FF*.fits')    
        else:
            ffs = glob.glob1(arch_dir, 'FF*.fits')
        if len(ffs) > 0:
            uploadffs = random.sample(ffs, min(2, len(ffs)))
            for ff in uploadffs:
                uploadlist.append({'dir_file':ff, 'file_ext': '.fits', 'src_dir': arch_dir})
    max_retries=5
    retry_wait = 60
    if len(uploadlist) > 1:
        for ent in uploadlist:
            retry = 0
            res = False
            while res is False and retry < max_retries:
                res = uploadOneFile(ent['src_dir'], ent['dir_file'], s3, targf, ent['file_ext'], keys) 
                if res is False:
                    sleep(retry_wait)
                    retry +=1
    return keys


def getListOfStations(srcdir):
    camfile = os.path.join(srcdir, 'cameras.ini')
    if not os.path.isfile(camfile):
        return [(None,'')]
    camcfg = configparser.ConfigParser()
    camcfg.read(camfile)
    return camcfg['cameras'].items()



def manualUpload(targ_dir, stationid, sciencefiles=False):
    """ Manually send the target folder to ukmon archive.  

    Args:  
        targ_dir (str): the full path to the target folder 

    You can invoke this function by opening a Terminal window and typing:  
    *python ../ukmon-pitools/uploadToArchive.py /path/to/target/folder*  

    If the argument is 'test' then a test file is uploaded and the status reported back.  
    """
    if targ_dir == 'test':
        myloc = os.path.split(os.path.abspath(__file__))[0]
        stations = getListOfStations(myloc)
        for cam in stations:
            stationid = cam[0]
            inifvals = readIniFile(os.path.join(myloc, 'ukmon.ini'), stationid)
            if inifvals['LOCATION']=='NOTCONFIGURED':
                continue
            if stationid is not None:
                stationid = stationid.upper()
            if not os.path.isfile(os.path.join(myloc, 'live.key')):
                if not getLatestKeys(myloc, stationid):
                    print('unable to get key for', inifvals['LOCATION'])
                    continue
            keys = readKeyFile(os.path.join(myloc, 'live.key'), inifvals)
            if not keys:
                continue
            with open('/tmp/test.txt', 'w') as f:
                f.write('{}'.format(inifvals['LOCATION']))

            target = keys['ARCHBUCKET']
            reg = keys['ARCHREGION']
            conn = boto3.Session(aws_access_key_id=keys['AWS_ACCESS_KEY_ID'], aws_secret_access_key=keys['AWS_SECRET_ACCESS_KEY']) 
            s3 = conn.resource('s3', region_name=reg)
            s3.meta.client.upload_file('/tmp/test.txt', target, 'tmp/{}.txt'.format(keys['CAMLOC']))
            stationid = '' if stationid is None else stationid
            print('test successful for', inifvals['LOCATION'], stationid)
        try:
            os.remove('/tmp/test.txt')
        except Exception:
            pass
        return True
    else:
        arch_dir = os.path.expanduser(targ_dir)
        if not os.path.isdir(arch_dir):
            print('folder {} not found'.format(arch_dir))
            return False
        return uploadToArchive(arch_dir, stationid, sciencefiles, keys=None)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('usage: python uploadToArchive.py dated_dir ')
        print('   eg: python uploadToArchive.py  UK001L_20260104_171228_956526')
        print('Optionally include the full path otherwise RMSs ArchivedFiles folder is assumed')
        exit(0)
    targdir = os.path.normpath(os.path.expanduser(sys.argv[1]))
    if targdir != 'test':
        nightdir = os.path.split(targdir)[1]
        stationid = nightdir.split('_')[0]
        manualUpload(targdir, stationid, sciencefiles=True)
        manualUpload(targdir, stationid, sciencefiles=False)
    else:
        manualUpload(targdir, None, sciencefiles=True)
