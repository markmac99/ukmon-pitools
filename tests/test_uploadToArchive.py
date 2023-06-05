# tests for uploadToArchive

import boto3
import os
from uploadToArchive import readKeyFile, uploadOneFile, manualUpload
from ukmonInstaller import createDefaultIni

basedir = os.path.realpath(os.path.dirname(__file__))
tmpdir = os.path.join(basedir, 'output')
if not os.path.isdir(tmpdir):
    os.makedirs(tmpdir)


def test_readKeyFile():
    vals = readKeyFile(os.path.join(basedir,'..','live.key'))
    assert vals['S3FOLDER'] == 'archive/Tackley'


def test_readKeyfileIni():
    homedir = os.path.join(basedir, 'output')
    createDefaultIni(homedir)
    vals = readKeyFile(os.path.join(homedir,'ukmon.ini'))
    os.remove(os.path.join(homedir,'ukmon.ini'))
    assert vals['RMSCFG'] == '~/source/RMS/.config'


def test_uploadOneFile():
    keys = readKeyFile(os.path.join(basedir,'..','live.key'))
    reg = keys['ARCHREGION']
    conn = boto3.Session(aws_access_key_id=keys['AWS_ACCESS_KEY_ID'], aws_secret_access_key=keys['AWS_SECRET_ACCESS_KEY']) 
    s3 = conn.resource('s3', region_name=reg)
    targf = keys['S3FOLDER']
    arch_dir = os.path.join(basedir, 'ukmarch','testpi4_20230401')
    dir_file = 'test.json'
    file_ext = '.json'
    uploadOneFile(arch_dir, dir_file, s3, targf, file_ext, keys)
    outf = os.path.join(basedir, 'output', 'foobar.txt')
    testkey = '{}/testpi4/2023/202304/20230401/test.json'.format(targf)
    s3.meta.client.download_file(keys['ARCHBUCKET'], testkey, outf)
    lis = open(outf,'r').readlines()
    assert lis[0].strip() == '{ "foo": "bar" }'
    os.remove(outf)


def test_manualUpload():
    targ_dir = 'test'
    assert manualUpload(targ_dir) is True
    targ_dir = os.path.join(basedir, 'ukmarch','testpi4_20230401')
    # create some dummy sample files
    testfilelist = ['FF_test_20230401.fits','FF_test_20230401.jpg','FF_test_20230401.mp4','mask.bmp',
                    'platepars_all_recalibrated.json',
                    'FTPdetectinfo_testpi4_20230401.txt',
                    'stack_.jpg','calib.jpg', '.config'
                    ]
    for fil in testfilelist:
        open(os.path.join(targ_dir, fil), 'w').write('{"test":"potato"}')
    assert manualUpload(targ_dir) is True
    for fil in testfilelist:
        os.remove(os.path.join(targ_dir, fil))
