# 
# Upload to ukmon from Python
#

import boto3
import os


def uploadOneFile(fname):
    print(fname)
    return


def uploadToArchive(arch_dir):
    dir_contents = os.listdir(arch_dir)
    for dir_file in dir_contents:
        file_name, file_ext = os.path.splitext(dir_file)
        file_ext = file_ext.lower()
        if ('FTPdetectinfo' in dir_file) and (file_ext == '.txt') and ('_original' not in file_name) and ('_backup' not in file_name):
            uploadOneFile(dir_file)
        if (file_ext == '.mp4') and ('FF_' in file_name):
            uploadOneFile(dir_file)
        elif file_ext in ('.jpg', '.kml', '.cal', '.json', '.csv') and ('DETECTED' not in file_name) and ('CAPTURED' not in file_name): 
            uploadOneFile(dir_file)
        elif dir_file == 'mask.bmp' or dir_file == 'flat.bmp' or dir_file == '.config':
            uploadOneFile(dir_file)
    return
