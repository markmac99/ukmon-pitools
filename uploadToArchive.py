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

log = logging.getLogger("logger")


def readKeyFile(filename):
    if not os.path.isfile(filename):
        print('credentials file missing, cannot continue')
        return None
    with open(filename, 'r') as fin:
        lis = fin.readlines()
    vals = {}
    for li in lis:
        if li[0]=='#':
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
    if 'LIVE_ACCESS_KEY_ID' not in vals and 'AWS_ACCESS_KEY_ID' in vals:
        vals['LIVE_ACCESS_KEY_ID'] = vals['AWS_ACCESS_KEY_ID']
    if 'LIVE_SECRET_ACCESS_KEY' not in vals and 'AWS_SECRET_ACCESS_KEY' in vals:
        vals['LIVE_SECRET_ACCESS_KEY'] = vals['AWS_SECRET_ACCESS_KEY']

    #print(vals)
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


def uploadToArchive(arch_dir):
    # Upload all relevant files from *arch_dir* to ukmon's S3 Archive

    myloc = os.path.split(os.path.abspath(__file__))[0]
    keyfile = os.path.join(myloc, 'live.key')
    if os.path.isfile(keyfile) is False:
        log.info('AWS keyfile not present')
        return False

    keys = readKeyFile(keyfile)
    if keys is None:
        print('keyfile not found, aborting')
        return False
    reg = keys['ARCHREGION']
    conn = boto3.Session(aws_access_key_id=keys['AWS_ACCESS_KEY_ID'], aws_secret_access_key=keys['AWS_SECRET_ACCESS_KEY']) 
    s3 = conn.resource('s3', region_name=reg)
    targf = keys['S3FOLDER']

    # upload the files but make sure we do the platepars file before the FTP file
    # otherwise there's a risk the matching engine will miss it
    dir_contents = os.listdir(arch_dir)
    daydir = os.path.split(arch_dir)[1]

    uploadlist = []
    # platepar must be uploaded before FTPdetect and config files
    uploadlist.append({'dir_file':'platepars_all_recalibrated.json', 'file_ext': '.json', 'src_dir': arch_dir})
    uploadlist.append({'dir_file':'.config', 'file_ext': '.config', 'src_dir': arch_dir})
    for dir_file in dir_contents:
        file_name, file_ext = os.path.splitext(dir_file)
        file_ext = file_ext.lower()
        if ('FTPdetectinfo_{}.txt'.format(daydir) == dir_file):
            uploadlist.append({'dir_file':dir_file, 'file_ext': file_ext, 'src_dir': arch_dir})
        # mp4 must be uploaded before corresponding jpg
        elif (file_ext == '.jpg') and ('FF_' in file_name):
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
        #elif dir_file == '.config':
        #    uploadlist.append({'dir_file':dir_file, 'file_ext': file_ext, 'src_dir': arch_dir})
    
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
    return res


def manualUpload(targ_dir):
    """ Manually send the target folder to ukmon archive.  

    Args:  
        targ_dir (str): the full path to the target folder 

    You can invoke this function by opening a Terminal window and typing:  
    *python ../ukmon-pitools/uploadToArchive.py /path/to/target/folder*  

    If the argument is 'test' then a test file is uploaded and the status reported back.  
    """
    if targ_dir == 'test':
        try:
            myloc = os.path.split(os.path.abspath(__file__))[0]
            filename = os.path.join(myloc, 'live.key')
            keys = readKeyFile(filename)
            if keys is None:
                print('keyfile not found, aborting')
                return False

            inifvals = readKeyFile(os.path.join(myloc, 'ukmon.ini'))
            with open('/tmp/test.txt', 'w') as f:
                f.write('{}'.format(inifvals['LOCATION']))

            target = keys['ARCHBUCKET']
            reg = keys['ARCHREGION']
            conn = boto3.Session(aws_access_key_id=keys['AWS_ACCESS_KEY_ID'], aws_secret_access_key=keys['AWS_SECRET_ACCESS_KEY']) 
            s3 = conn.resource('s3', region_name=reg)
            s3.meta.client.upload_file('/tmp/test.txt', target, 'tmp/{}.txt'.format(keys['CAMLOC']))
            #key = {'Objects': []}
            #key['Objects'] = [{'Key': 'test.txt'}]
            #s3.meta.client.delete_objects(Bucket=target, Delete=key)
            print('test successful')
        except Exception:
            print('unable to upload to archive - check key information')
            return False
        try:
            os.remove('/tmp/test.txt')
        except Exception:
            pass
        return True
    else:
        arch_dir = os.path.join(targ_dir)
        return uploadToArchive(arch_dir)


if __name__ == '__main__':
    manualUpload(sys.argv[1])
