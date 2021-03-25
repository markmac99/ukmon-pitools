#
# python script to upload one event to ukmon-live
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
import configparser


def uploadOneEvent(cap_dir, dir_file, loc, s3):
    print('{:s} {:s} {:s} {:s}'.format(cap_dir, dir_file, loc[4], loc[3]), flush=True)

    target = 'ukmon-live'
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
    bff.batchFFtoImage(tmpdir, 'jpg')
    file_name, _ = os.path.splitext(dir_file)
    ojpgname = file_name + '.jpg'
    njpgname = 'M' + ymd + '_' + hms + '_' + loc[4] + '_' + camid + 'P.jpg'
    fulljpg = os.path.join(tmpdir, njpgname)
    os.rename(os.path.join(tmpdir, ojpgname), fulljpg)

    xmlname = 'M' + ymd + '_' + hms + '_' + loc[4] + '_' + camid + '.xml'
    fullxml = os.path.join(tmpdir, xmlname)
    with open(fullxml, 'w') as ofl:
        ofl.write('<?xml version="1.0" encoding="UTF-8" ?>\n')
        ofl.write('<ufocapture_record version="215" ')
        ofl.write('y="{:s}" mo="{:s}" d="{:s}" h="{:s}" m="{:s}" s="{:s}" '.format(yr, mth, dy, hr, mi, se))
        ofl.write('trig="1" frames="68" lng="{:.4f}" lat="{:.4f}" alt="{:.1f}" '.format(loc[1], loc[0], loc[2]))
        ofl.write('tz="0" u2="224" cx="1280" cy="720" fps="25.000" head="30" ')
        ofl.write('tail="30" diff="2" sipos="6" sisize="15" dlev="40" dsize="4" ')
        ofl.write('lid="{:s}" observer="" sid="{:s}" cam="{:s}" lens="" cap="" '.format(loc[4], camid, camid))
        ofl.write('comment="" interlace="1" bbf="0" dropframe="0">\n')
        ofl.write('    <ufocapture_paths hit="3">\n')
        ofl.write('     <uc_path fno="30" ono="18" pixel="3" bmax="79" x="395.7" y="282.3"></uc_path>\n')
        ofl.write('     <uc_path fno="30" ono="18" pixel="9" bmax="96" x="393.6" y="288.1"></uc_path>\n')
        ofl.write('     <uc_path fno="31" ono="18" pixel="16" bmax="112" x="391.1" y="295.5"></uc_path>\n')
        ofl.write('    </ufocapture_paths>\n')
        ofl.write('</ufocapture_record>\n')

    s3.meta.client.upload_file(fulljpg, target, njpgname, ExtraArgs={'ContentType': 'image/jpeg'})
    s3.meta.client.upload_file(fullxml, target, xmlname, ExtraArgs={'ContentType': 'application/xml'})
    print(njpgname)
    shutil.rmtree(tmpdir)
    return


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('usage: python sendToLive.py capdir ffname')
        exit(1)

    camloc = None
    awskey = None
    awssec = None
    awsreg = None
    myloc = os.path.split(os.path.abspath(__file__))[0]
    # get camera location from ini file
    with open(os.path.join(myloc, 'ukmon.ini'), 'r') as inif:
        lines = inif.readlines()
        for li in lines:
            if 'LOCATION' in li:
                camloc = li.split('=')[1].strip()
                break
    if camloc is None:
        print('LOCATION not found in ini file, aborting')
        exit(1)

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
    # read a few variables from the RMS config file
    cfg = configparser.ConfigParser()
    cfg.read('/home/pi/source/RMS/.config')
    loc = []
    loc.append(float(cfg['System']['latitude'].split()[0]))
    loc.append(float(cfg['System']['longitude'].split()[0]))
    loc.append(float(cfg['System']['elevation'].split()[0]))
    loc.append(cfg['System']['stationID'].split()[0])
    loc.append(camloc)

    uploadOneEvent(sys.argv[1], sys.argv[2], loc, s3)
