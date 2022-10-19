# 
# Upload to ukmon from Python
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
import datetime
import json
import random
import glob
import configparser


def readKeyFile(filename):
    if not os.path.isfile(filename):
        print('credentials file missing, cannot continue')
        exit(1)
    with open(filename, 'r') as fin:
        lis = fin.readlines()
    vals = {}
    for li in lis:
        if li[0]=='#':
            continue
        if '=' in li:
            valstr = li.split(' ')[1]
            data = valstr.split('=')
            val = data[1].strip()
            if val[0]=='"':
                val = val[1:len(val)-1]
            vals[data[0]] = val
    
    if 'S3FOLDER' not in vals and 'CAMLOC' in vals:
        vals['S3FOLDER'] = f'archive/{vals["CAMLOC"]}'
        if vals['S3FOLDER'][-1] =='/':
            vals['S3FOLDER'] = vals['S3FOLDER'][:-1]
    if 'ARCHBUCKET' not in vals:
        vals['ARCHBUCKET'] = 'ukmon-shared'
    if 'LIVEBUCKET' not in vals:
        vals['LIVEBUCKET'] = 'ukmon-live'
    if 'WEBBUCKET' not in vals:
        vals['WEBBUCKET'] = 'ukmeteornetworkarchive'
    if 'ARCHREGION' not in vals:
        vals['ARCHREGION'] = 'eu-west-2'
    if 'LIVEREGION' not in vals:
        vals['LIVEREGION'] = 'eu-west-1'
    if 'MATCHDIR' not in vals:
        vals['MATCHDIR'] = 'matches/RMSCorrelate'
    #print(vals)
    return vals


def uploadOneFile(arch_dir, dir_file, s3, targf, file_ext, keys, log=None, force_matchdir=False):
    # upload a single file to ukmon, setting the mime type accordingly
    
    target = keys['ARCHBUCKET']
    daydir = os.path.split(arch_dir)[1]
    spls = daydir.split('_')
    camid = spls[0]
    ymd = spls[1]
    desf= f'{targf}/{camid}/{ymd[:4]}/{ymd[:6]}/{ymd}/{dir_file}'
    ctyp='text/plain'
    if file_ext=='.jpg': 
        ctyp = 'image/jpeg'
        if 'FF_' in dir_file:
            target=keys['WEBBUCKET']
            desf = f'img/single/{ymd[:4]}/{ymd[:6]}/{dir_file}'
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
            desf = f'img/mp4/{ymd[:4]}/{ymd[:6]}/{dir_file}'
    elif file_ext=='.csv': 
        ctyp = 'text/csv'
    elif file_ext=='.json':
        ctyp = 'application/json'
        if 'platepars_all' in dir_file: 
            desf = f'{keys["MATCHDIR"]}/{camid}/{daydir}/{dir_file}'
    elif dir_file == f'FTPdetectinfo_{daydir}.txt': 
        ctyp = 'text/plain'
        desf = f'{keys["MATCHDIR"]}/{camid}/{daydir}/{dir_file}'

    if force_matchdir is True:
        desf = f'{keys["MATCHDIR"]}/{camid}/{daydir}/{dir_file}'

    srcf = os.path.join(arch_dir, dir_file)
    try:
        s3.meta.client.upload_file(srcf, target, desf, ExtraArgs={'ContentType': ctyp})
        if log is None:
            print(desf)
        else:
            log.info(desf)
    except Exception:
        if log is None:
            print('upload failed: {}'.format(dir_file))
        else:
            log.info('upload failed: {}'.format(dir_file))
    return


def uploadToArchive(arch_dir, log=None):
    # Upload all relevant files from *arch_dir* to ukmon's S3 Archive

    myloc = os.path.split(os.path.abspath(__file__))[0]
    keyfile = os.path.join(myloc, 'live.key')
    if os.path.isfile(keyfile) is False:
        log.info('AWS keyfile not present')
        return

    keys = readKeyFile(keyfile)
    reg = keys['ARCHREGION']
    conn = boto3.Session(aws_access_key_id=keys['AWS_ACCESS_KEY_ID'], aws_secret_access_key=keys['AWS_SECRET_ACCESS_KEY']) 
    s3 = conn.resource('s3', region_name=reg)
    targf = keys['S3FOLDER']

    # upload the files but make sure we do the platepars file before the FTP file
    # otherwise there's a risk the matching engine will miss it
    dir_contents = os.listdir(arch_dir)
    daydir = os.path.split(arch_dir)[1]
    for dir_file in dir_contents:
        file_name, file_ext = os.path.splitext(dir_file)
        file_ext = file_ext.lower()
        # platepar must be uploaded before FTPdetect file
        if (f'FTPdetectinfo_{daydir}.txt' == dir_file):
            if os.path.isfile(os.path.join(arch_dir, 'platepars_all_recalibrated.json')):
                uploadOneFile(arch_dir, 'platepars_all_recalibrated.json', s3, targf, '.json', keys, log)
            uploadOneFile(arch_dir, dir_file, s3, targf, file_ext, keys, log)
        # mp4 must be uploaded before corresponding jpg
        elif (file_ext == '.jpg') and ('FF_' in file_name):
            mp4f = dir_file.replace('.jpg', '.mp4')
            if os.path.isfile(os.path.join(arch_dir, mp4f)):
                uploadOneFile(arch_dir, mp4f, s3, targf, '.mp4', keys, log)
            uploadOneFile(arch_dir, dir_file, s3, targf, file_ext, keys, log)
        elif (file_ext == '.jpg') and ('stack_' in file_name) and ('track' not in file_name):
            uploadOneFile(arch_dir, dir_file, s3, targf, file_ext, keys, log)
        elif (file_ext == '.jpg') and ('calib' in file_name):
            uploadOneFile(arch_dir, dir_file, s3, targf, file_ext, keys, log)
        elif file_ext in ('.png', '.kml', '.cal', '.json', '.csv'): 
            uploadOneFile(arch_dir, dir_file, s3, targf, file_ext, keys, log)
        elif dir_file == 'mask.bmp' or dir_file == 'flat.bmp':
            uploadOneFile(arch_dir, dir_file, s3, targf, file_ext, keys, log)
        elif dir_file == '.config':
            uploadOneFile(arch_dir, dir_file, s3, targf, file_ext, keys, log)
            uploadOneFile(arch_dir, dir_file, s3, targf, file_ext, keys, log, True)
    
    # upload two FITs files chosen at random from the recalibrated ones
    # to be used for platepar creation if needed
    if os.path.isfile(os.path.join(arch_dir, 'platepars_all_recalibrated.json')):
        with open(os.path.join(arch_dir, 'platepars_all_recalibrated.json')) as ppf:
            js = json.load(ppf)
        ffs=[k for k in js.keys() if js[k]['auto_recalibrated'] is True]
    else:
        ffs = glob.glob1(arch_dir, 'FF*.fits')
    if len(ffs) > 0:
        cap_dir = arch_dir.replace('ArchivedFiles','CapturedFiles')
        uploadffs = random.sample(ffs, min(2, len(ffs)))
        for ff in uploadffs:
            uploadOneFile(cap_dir, ff, s3, targf, '.fits', keys, log)    

    return


def fireballUpload(ffname, log=None):
    # get camera location from ini file
    myloc = os.path.split(os.path.abspath(__file__))[0]
    inifvals = readKeyFile(os.path.join(myloc, 'ukmon.ini'))
    camloc = inifvals['LOCATION']
    rmscfg = inifvals['RMSCFG']
    if camloc == 'NOTCONFIGURED':
        print('LOCATION not found in ini file, aborting')
        exit(1)
    cfg = configparser.ConfigParser(inline_comment_prefixes=(';'))
    cfg.read(os.path.expanduser(rmscfg))

    rmsdatadir = os.path.expanduser(cfg['Capture']['data_dir'])

    myloc = os.path.split(os.path.abspath(__file__))[0]
    filename = os.path.join(myloc, 'live.key')
    keys = readKeyFile(filename)
    targf = keys['S3FOLDER']
    reg = keys['ARCHREGION']
    conn = boto3.Session(aws_access_key_id=keys['AWS_ACCESS_KEY_ID'], aws_secret_access_key=keys['AWS_SECRET_ACCESS_KEY']) 
    s3 = conn.resource('s3', region_name=reg)

    dtstamp = ffname[10:25]
    ts = datetime.datetime.strptime(dtstamp,'%Y%m%d_%H%M%S')
    if ts.hour < 12:
        ts = ts + datetime.timedelta(days=-1)
    dirpat = ts.strftime('%Y%m%d')
    basarc = os.path.join(rmsdatadir, 'CapturedFiles')
    cap_dirs = [name for name in os.listdir(basarc) if (os.path.isdir(os.path.join(basarc, name)) and dirpat in name)]
    if len(cap_dirs) > 0:
        fldr = cap_dirs[0]
#        arch_dir = os.path.join(basarc, fldr)
        cap_dir = os.path.join(rmsdatadir, 'CapturedFiles', fldr)
        fbname = 'FR' + ffname[2:-5] + '.bin'
        uploadOneFile(cap_dir, fbname, s3, targf, '.fits', keys, log)        
        uploadOneFile(cap_dir, ffname, s3, targf, '.fits', keys, log)        
    else:
        print('unable to find source folder')
    return


def manualUpload(targ_dir):
    """ Manually send the target folder to ukmon archive. 
    To invoke this function open a Terminal window and type

    *python ../ukmon-pitools/uploadToArchive.py /path/to/target/folder*

    You can also use this to test connectivity by passing a single parameter 'test'. 
    """
    if targ_dir == 'test':
        with open('/tmp/test.txt', 'w') as f:
            f.write('test')
        try:
            myloc = os.path.split(os.path.abspath(__file__))[0]
            filename = os.path.join(myloc, 'live.key')
            keys = readKeyFile(filename)
            target = keys['ARCHBUCKET']
            reg = keys['ARCHREGION']
            conn = boto3.Session(aws_access_key_id=keys['AWS_ACCESS_KEY_ID'], aws_secret_access_key=keys['AWS_SECRET_ACCESS_KEY']) 
            s3 = conn.resource('s3', region_name=reg)
            s3.meta.client.upload_file('/tmp/test.txt', target, 'test.txt')
            key = {'Objects': []}
            key['Objects'] = [{'Key': 'test.txt'}]
            s3.meta.client.delete_objects(Bucket=target, Delete=key)
            print('test successful')
        except Exception:
            print('unable to upload to archive - check key information')
        os.remove('/tmp/test.txt')
    else:
        arch_dir = os.path.join(targ_dir)
        uploadToArchive(arch_dir)


if __name__ == '__main__':
    manualUpload(sys.argv[1])
