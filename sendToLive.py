# Copyright (C) Mark McIntyre
#
# python script to upload one event to a target bucket for live feeds
#
# to use this file to manually upload a file do
#   python sendToLive.py cap_dir ff_name
#
import os
import sys
import Utils.BatchFFtoImage as bff
import shutil
import tempfile
import boto3
import glob
from uploadToArchive import readKeyFile
import logging
import RMS.ConfigReader as cr
import numpy as np
from RMS.Formats.FieldIntensities import readFieldIntensitiesBin


log = logging.getLogger("logger")


def checkFbUpload(stationid, datadir, s3):
    archbuck = os.getenv('ARCHBUCKET', default='ukmon-shared')
    listfile = stationid.lower() + '.txt'
    locfile = os.path.join('/tmp',listfile)
    remfile = 'fireballs/interesting/' + listfile
    capdir = os.path.join(datadir, 'CapturedFiles')
    capdirs = os.listdir(capdir)
    try: 
        objlist =s3.meta.client.list_objects_v2(Bucket=archbuck, Prefix=remfile)
        if objlist['KeyCount'] > 0:
            log.info('fireball upload requested')
            try: 
                s3.meta.client.download_file(archbuck, remfile, locfile)
                for fname in open(locfile,'r').readlines():
                    if len(fname) < 5: 
                        continue
                    got = 0
                    for thisdir in capdirs:
                        srcpatt=os.path.join(capdir, thisdir, '*' + fname.strip() + '*')
                        #log.info('requested pattern {}'.format(srcpatt))
                        srclist = glob.glob(srcpatt)
                        for srcfile in srclist: 
                            _, thisfname = os.path.split(srcfile)
                            targfile = 'fireballs/interesting/' + thisfname
                            try: 
                                s3.meta.client.upload_file(srcfile, archbuck, targfile)
                                log.info('uploaded {}'.format(srcfile))
                                got = 1
                            except Exception as e:
                                log.info(e, exc_info=True)
                    if got == 0:
                        log.info(f'file {fname.strip()} not found')
                            
                os.remove(locfile)
                key = {'Objects': []}
                key['Objects'] = [{'Key': remfile}]
                s3.meta.client.delete_objects(Bucket=archbuck, Delete=key)
            except Exception as e:
                log.warning('unable to download trigger file')
                log.info(e, exc_info=True)
    except Exception as e:
        log.warning('unable to scan S3 for trigger file')
        log.info(e, exc_info=True)


def getBlockBrightness(dirpath, filename):
    filename = filename.replace('FF_', 'FS_')
    filename = filename.replace('.fits', '_fieldsum.bin')
    frnos, intens = readFieldIntensitiesBin(dirpath, filename)
    maxInten = max(intens)
    avgInten = int(np.average(intens))
    stdInten = int(np.std(intens))
    idx = np.argwhere(intens == maxInten)[0][0]
    maxFr = int(frnos[idx])
    return {'max':maxInten, 'avg':avgInten, 'stddev':stdInten, 'frNo':maxFr}


def uploadOneEvent(cap_dir, dir_file, cfg, s3, camloc):
    target = os.getenv('LIVEBUCK', default='ukmon-live')
    spls = dir_file.split('_')
    camid = spls[1]
    ymd = spls[2]
    hms = spls[3]
    millis = spls[4]
    yr = ymd[:4]
    mth = ymd[4:6]
    dy = ymd[6:8]
    hr = hms[:2]
    mi = hms[2:4]
    se = hms[4:6]
    se = se + '.{:.2f}'.format(float(millis)/1000)
    tmpdir = tempfile.mkdtemp()
    shutil.copy2(os.path.join(cap_dir, dir_file), tmpdir)
    try:
        bff.batchFFtoImage(tmpdir, 'jpg', True)
    except:
        bff.batchFFtoImage(tmpdir, 'jpg')
    file_name, _ = os.path.splitext(dir_file)
    ojpgname = file_name + '.jpg'
    njpgname = 'M' + ymd + '_' + hms + '_' + camloc + '_' + camid + 'P.jpg'
    fulljpg = os.path.join(tmpdir, njpgname)
    os.rename(os.path.join(tmpdir, ojpgname), fulljpg)

    camid = cfg.stationID

    briInfo = getBlockBrightness(cap_dir, dir_file)

    xmlname = 'M' + ymd + '_' + hms + '_' + camloc + '_' + camid + '.xml'
    fullxml = os.path.join(tmpdir, xmlname)
    with open(fullxml, 'w') as ofl:
        ofl.write('<?xml version="1.0" encoding="UTF-8" ?>\n')
        ofl.write('<ufocapture_record version="215" ')
        ofl.write('y="{:s}" mo="{:s}" d="{:s}" h="{:s}" m="{:s}" s="{:s}" '.format(yr, mth, dy, hr, mi, se))
        ofl.write('trig="1" frames="68" lng="{:.4f}" lat="{:.4f}" alt="{:.1f}" '.format(cfg.longitude, cfg.latitude, cfg.elevation))
        ofl.write('tz="0" u2="224" cx="1280" cy="720" fps="25.000" head="30" ')
        ofl.write('tail="30" diff="2" sipos="6" sisize="15" dlev="40" dsize="4" ')
        ofl.write('lid="{:s}" observer="" sid="{:s}" cam="{:s}" lens="" cap="{}" '.format(camloc, camid, camid, dir_file))
        ofl.write('comment="" interlace="1" bbf="0" dropframe="0">\n')
        ofl.write('    <ufocapture_paths hit="3">\n')
        # the three lines are max, average and stdev of frame brightnesses  
        ofl.write('     <uc_path fno="{}" ono="18" pixel="3" bmax="{}" x="395.7" y="282.3"></uc_path>\n'.format(briInfo['frNo'], briInfo['max']))
        ofl.write('     <uc_path fno="{}" ono="18" pixel="9" bmax="{}" x="393.6" y="288.1"></uc_path>\n'.format(briInfo['frNo']+1, briInfo['avg']))
        ofl.write('     <uc_path fno="{}" ono="18" pixel="16" bmax="{}" x="391.1" y="295.5"></uc_path>\n'.format(briInfo['frNo']+2, briInfo['std']))
        ofl.write('    </ufocapture_paths>\n')
        ofl.write('</ufocapture_record>\n')

    try: 
        s3.meta.client.upload_file(fulljpg, target, njpgname, ExtraArgs={'ContentType': 'image/jpeg'})
        s3.meta.client.upload_file(fullxml, target, xmlname, ExtraArgs={'ContentType': 'application/xml'})
    except Exception as e:
        log.warning('unable to upload to livestream')
        log.info(e, exc_info=True)

    sys.stdout.flush()
    shutil.rmtree(tmpdir)
    return


def singleUpload(cap_dir, dir_file):
    """This function is used to manually upload a single event.
    It can also be used to test the connection - see note below. 

    To invoke this function, open a Terminal window and type

    *python ../ukmon-pitools/sendToLive.py cap_dir file_to_send* 

    args:
        cap_dir (str): capture dir OR the word 'test'
        file_to_send (str): file to upload OR the word 'test'

    Comments:
        If both arguments are 'test' then a test file is uploaded. 

    """

    camloc = None
    awskey = None
    awssec = None
    awsreg = None
    myloc = os.path.split(os.path.abspath(__file__))[0]
    # get camera location from ini file
    inifvals = readKeyFile(os.path.join(myloc, 'ukmon.ini'))
    camloc = inifvals['LOCATION']
    try:
        rmscfg = inifvals['RMSCFG']
    except:
        rmscfg='~/source/RMS/.config'
    if camloc == 'NOTCONFIGURED':
        print('LOCATION not found in ini file, aborting')
        exit(1)

    # get credentials
    keys = readKeyFile(os.path.join(myloc, 'live.key'))
    awskey = keys['AWS_ACCESS_KEY_ID']
    awssec = keys['AWS_SECRET_ACCESS_KEY']
    awsreg = keys['LIVEREGION']
    target = keys['LIVEBUCKET']

    conn = boto3.Session(aws_access_key_id=awskey, aws_secret_access_key=awssec, region_name=awsreg) 
    s3 = conn.resource('s3')
    # read a few variables from the RMS config file
    cfg = cr.parse(os.path.expanduser(rmscfg))

    if sys.argv[1] == 'test' and sys.argv[2] == 'test':
        with open('/tmp/test.txt', 'w') as f:
            f.write('test')
        
        try:
            s3.meta.client.upload_file('/tmp/test.txt', target, 'test.txt')
            key = {'Objects': []}
            key['Objects'] = [{'Key': 'test.txt'}]
            s3.meta.client.delete_objects(Bucket=target, Delete=key)
            print('test successful')
        except Exception:
            print('unable to upload to {} - check key information'.format(target))
        try:
            os.remove('/tmp/test.txt')
        except:
            pass
    else:
        uploadOneEvent(cap_dir, dir_file, cfg, s3, camloc)


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('usage: python sendToLive.py capdir ffname')
        exit(1)
    singleUpload(sys.argv[1], sys.argv[2])
