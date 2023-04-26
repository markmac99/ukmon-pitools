# tests for uploadToArchive

import boto3
import os
from uploadToArchive import readKeyFile, uploadOneFile
from ukmonInstaller import createDefaultIni

basedir = os.path.realpath(os.path.dirname(__file__))


def test_readKeyFile():
    vals = readKeyFile(os.path.join(basedir,'..','live.key'))
    assert vals['ARCHBUCKET'] == 'ukmon-shared'


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
    os.makedirs(os.path.join(basedir, 'output'), exist_ok=True)
    outf = os.path.join(basedir, 'output', 'foobar.txt')
    s3.meta.client.download_file(keys['ARCHBUCKET'], 'tmp/testpi4/2023/202304/20230401/test.json', outf)
    lis = open(outf,'r').readlines()
    assert lis[0] == 'foo\n'
    os.remove(outf)
