# 
# Upload to ukmon from Python
#

import boto3
import os
import sys


def uploadOneFile(arch_dir, dir_file, s3, targf):
    target = 'ukmon-shared'
    daydir = os.path.split(arch_dir)[1]
    spls = daydir.split('_')
    ymd = spls[1]

    srcf = os.path.join(arch_dir, dir_file)
    desf= targf + spls[0] + '/' + ymd[:4] + '/' + ymd[:6] + '/' + ymd + '/' + dir_file
    s3.meta.client.upload_file(srcf, target, desf)
    print(desf)
    return


def uploadToArchive(arch_dir):
    myloc = os.path.split(os.path.abspath(__file__))[0]
    filename = os.path.join(myloc, 'archive.key')
    with open(filename, 'r') as fin:
        key = fin.readline().split('=')[1]
        secr = fin.readline().split('=')[1]
        reg = fin.readline().split('=')[1]
        targf = fin.readline().split('=')[1]
    print(targf)    
    conn = boto3.Session(aws_access_key_id=key, aws_secret_access_key=secr, region_name=reg)
    s3 = conn.resource('s3')

    dir_contents = os.listdir(arch_dir)
    for dir_file in dir_contents:
        file_name, file_ext = os.path.splitext(dir_file)
        file_ext = file_ext.lower()
        if ('FTPdetectinfo' in dir_file) and (file_ext == '.txt') and ('_original' not in file_name) and ('_backup' not in file_name):
            uploadOneFile(arch_dir, dir_file, s3, targf)
        if (file_ext == '.mp4') and ('FF_' in file_name):
            uploadOneFile(arch_dir, dir_file, s3, targf)
        elif file_ext in ('.jpg', '.kml', '.cal', '.json', '.csv') and ('DETECTED' not in file_name) and ('CAPTURED' not in file_name): 
            uploadOneFile(arch_dir, dir_file, s3, targf)
        elif dir_file == 'mask.bmp' or dir_file == 'flat.bmp' or dir_file == '.config':
            uploadOneFile(arch_dir, dir_file, s3, targf)
    return


if __name__ == '__main__':
    arch_dir = os.path.join('/home/pi/RMS_data/ArchivedFiles/', sys.argv[1])
    uploadToArchive(arch_dir)
