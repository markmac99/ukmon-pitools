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
from uploadToArchive import readKeyFile
import logging
import RMS.ConfigReader as cr
import numpy as np
from RMS.Formats.FieldIntensities import readFieldIntensitiesBin


log = logging.getLogger("logger")


def getBlockBrightness(dirpath, filename):
    filename = filename.replace('FF_', 'FS_')
    filename = filename.replace('.fits', '_fieldsum.bin')
    if not os.path.isfile(os.path.join(dirpath, filename)):
        return {'max':99, 'avg':99, 'std':99, 'frNo':99}
    frnos, intens = readFieldIntensitiesBin(dirpath, filename)
    maxInten = max(intens)
    avgInten = int(np.average(intens))
    stdInten = int(np.std(intens))
    idx = np.argwhere(intens == maxInten)[0][0]
    maxFr = int(frnos[idx])
    return {'max':maxInten, 'avg':avgInten, 'std':stdInten, 'frNo':maxFr}


def createXMLfile(tmpdir, cap_dir, dir_file, camloc, cfg):
    camid = cfg.stationID
    briInfo = getBlockBrightness(cap_dir, dir_file)
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
    se = '{}.{}'.format(hms[4:6], millis)
    xmlname = 'M' + ymd + '_' + hms + '_' + camloc + '_' + camid + '.xml'
    fullxml = os.path.join(tmpdir, xmlname)
    with open(fullxml, 'w') as ofl:
        ofl.write('<?xml version="1.0" encoding="UTF-8" ?>\n')
        ofl.write('<ufocapture_record version="215" ')
        ofl.write('y="{:s}" mo="{:s}" d="{:s}" h="{:s}" m="{:s}" s="{:s}" '.format(yr, mth, dy, hr, mi, se))
        ofl.write('trig="1" frames="68" lng="{:.4f}" lat="{:.4f}" alt="{:.1f}" '.format(cfg.longitude, cfg.latitude, cfg.elevation))
        ofl.write('tz="0" u2="224" cx="{}" cy="{}" fps="{:.3f}" head="30" '.format(cfg.width, cfg.height, cfg.fps))
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
    return fullxml, xmlname


def createJpg(tmpdir, cap_dir, dir_file, camloc):
    spls = dir_file.split('_')
    camid = spls[1]
    ymd = spls[2]
    hms = spls[3]

    shutil.copy2(os.path.join(cap_dir, dir_file), tmpdir)
    try:
        bff.batchFFtoImage(tmpdir, 'jpg', True)
    except Exception:
        bff.batchFFtoImage(tmpdir, 'jpg')
    file_name, _ = os.path.splitext(dir_file)
    ojpgname = file_name + '.jpg'
    njpgname = 'M' + ymd + '_' + hms + '_' + camloc + '_' + camid + 'P.jpg'
    fulljpg = os.path.join(tmpdir, njpgname)
    if os.path.isfile(fulljpg):
        os.remove(fulljpg)
    os.rename(os.path.join(tmpdir, ojpgname), fulljpg)
    return fulljpg, njpgname


def uploadOneEvent(cap_dir, dir_file, cfg, keys, camloc):
    oldconn = boto3.Session(aws_access_key_id=keys['LIVE_ACCESS_KEY_ID'], 
                            aws_secret_access_key=keys['LIVE_SECRET_ACCESS_KEY'], region_name=keys['LIVEREGION']) 
    s3old = oldconn.resource('s3')
    oldbuck = keys['LIVEBUCKET']
    mdaconn = boto3.Session(aws_access_key_id=keys['AWS_ACCESS_KEY_ID'], 
                          aws_secret_access_key=keys['AWS_SECRET_ACCESS_KEY'], region_name=keys['AWS_DEFAULT_REGION'])
    s3mda = mdaconn.resource('s3')
    mdabuck = keys['ARCHBUCKET'].replace('shared','live')

    tmpdir = tempfile.mkdtemp()
    if not os.path.isfile(os.path.join(cap_dir, dir_file)):
        retmsg = '{} not present in {}'.format(dir_file, cap_dir)
        log.warning(retmsg)
        return retmsg
    fulljpg, njpgname = createJpg(tmpdir, cap_dir, dir_file, camloc) 
    fullxml, xmlname = createXMLfile(tmpdir, cap_dir, dir_file, camloc, cfg)
    for s3, target in zip((s3old, s3mda), (oldbuck, mdabuck)):
        try: 
            s3.meta.client.upload_file(fulljpg, target, njpgname, ExtraArgs={'ContentType': 'image/jpeg'})
            s3.meta.client.upload_file(fullxml, target, xmlname, ExtraArgs={'ContentType': 'application/xml'})
            retmsg = 'upload of {} successful'.format(njpgname)
        except Exception as e:
            retmsg = 'unable to upload to {}'.format(target)
            log.warning(retmsg)
            log.info(e, exc_info=True)
    sys.stdout.flush()
    shutil.rmtree(tmpdir)
    return retmsg


def testFeed(keys, cfg):
    camid = cfg.stationID
    with open('/tmp/test.txt', 'w') as f:
        f.write('{}'.format(camid))
    oldconn = boto3.Session(aws_access_key_id=keys['LIVE_ACCESS_KEY_ID'], 
                            aws_secret_access_key=keys['LIVE_SECRET_ACCESS_KEY'], region_name=keys['LIVEREGION']) 
    s3old = oldconn.resource('s3')
    oldbuck = keys['LIVEBUCKET']
    mdaconn = boto3.Session(aws_access_key_id=keys['AWS_ACCESS_KEY_ID'], 
                            aws_secret_access_key=keys['AWS_SECRET_ACCESS_KEY'], region_name=keys['AWS_DEFAULT_REGION'])
    s3mda = mdaconn.resource('s3')
    mdabuck = keys['ARCHBUCKET'].replace('shared','live')
    for s3, target in zip((s3old, s3mda), (oldbuck, mdabuck)):
        try:
            s3.meta.client.upload_file('/tmp/test.txt', target, 'test/{}_{}.txt'.format(keys['CAMLOC'], camid))
            retmsg = 'test successful'
        except Exception:
            retmsg = 'unable to upload to {} - check key information'.format(target)
    try:
        os.remove('/tmp/test.txt')
    except Exception:
        pass
    return retmsg


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
    myloc = os.path.split(os.path.abspath(__file__))[0]
    # get camera location from ini file
    inifvals = readKeyFile(os.path.join(myloc, 'ukmon.ini'))
    if inifvals is None:
        log.warning('unable to open ini file')
        return 'unable to open ini file'
    camloc = inifvals['LOCATION']
    try:
        rmscfg = inifvals['RMSCFG']
    except Exception:
        rmscfg='~/source/RMS/.config'
    if camloc == 'NOTCONFIGURED':
        print('LOCATION not found in ini file, aborting')
        return 'not configured'

    # get credentials
    keys = readKeyFile(os.path.join(myloc, 'live.key'))
    if keys is None:
        log.warning('unable to open keyfile')
        return 'unable to open keyfile'

    # read a few variables from the RMS config file
    cfg = cr.parse(os.path.expanduser(rmscfg))
#    configpath, configname = os.path.split(os.path.expanduser(rmscfg))
#    cfg = cr.loadConfigFromDirectory(configname, configpath)

    if cap_dir == 'test' and dir_file == 'test':
        retmsg = testFeed(keys, cfg)
    else:
        retmsg = uploadOneEvent(cap_dir, dir_file, cfg, keys, camloc)
    return retmsg


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('usage: python sendToLive.py capdir ffname')
        exit(1)
    retmsg = singleUpload(sys.argv[1], sys.argv[2])
    print(retmsg)
