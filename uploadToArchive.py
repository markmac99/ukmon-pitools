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


def uploadOneFile(arch_dir, dir_file, s3, targf, file_ext):
    """ Upload a single named file to the UKmon Archive

    Args:
        arch_dir (str): full path to ArchivedFiles dated folder 
        dir_file (str): file to uoload 
        s3 (obj): AWS S3 object
        targf (str): full name of target file including folders
        file_ext (str): file type, used to set MIME type correctly

    """
    target = 'ukmon-shared'
    daydir = os.path.split(arch_dir)[1]
    spls = daydir.split('_')
    camid = spls[0]
    ymd = spls[1]
    ctyp='text/plain'
    if file_ext=='.jpg': 
        ctyp = 'image/jpeg'
    elif file_ext=='.png': 
        ctyp = 'image/png'
    elif file_ext=='.bmp': 
        ctyp = 'image/bmp'
    elif file_ext=='.mp4': 
        ctyp = 'vide0/mp4'
    if file_ext=='.csv': 
        ctyp = 'text/csv'
    elif file_ext=='.json': 
        ctyp = 'application/json'

    srcf = os.path.join(arch_dir, dir_file)
    desf= targf + camid + '/' + ymd[:4] + '/' + ymd[:6] + '/' + ymd + '/' + dir_file
    try:
        s3.meta.client.upload_file(srcf, target, desf, ExtraArgs={'ContentType': ctyp})
        print(desf)
    except Exception:
        print('file not present: {}'.format(dir_file))
    return


def uploadToArchive(arch_dir):
    """ Upload all relevant files from *arch_dir* to ukmon's S3 Archive

    Args:
        arch_dir (str): full path to the ArchivedFiles folder to be processed

    """
    myloc = os.path.split(os.path.abspath(__file__))[0]
    filename = os.path.join(myloc, 'archive.key')
    with open(filename, 'r') as fin:
        key = fin.readline().split('=')[1].strip()
        secr = fin.readline().split('=')[1].strip()
        reg = fin.readline().split('=')[1].strip()
        targf = fin.readline().split('=')[1].strip()
    if targf[0] == '"':
        targf = targf[1:len(targf)-1]
    conn = boto3.Session(aws_access_key_id=key, aws_secret_access_key=secr) 
    s3 = conn.resource('s3', region_name=reg)

    # upload the files but make sure we do the platepars file before the FTP file
    # otherwise there's a risk the matching engine will miss it
    dir_contents = os.listdir(arch_dir)
    for dir_file in dir_contents:
        file_name, file_ext = os.path.splitext(dir_file)
        file_ext = file_ext.lower()
        if ('FTPdetectinfo' in dir_file) and (file_ext == '.txt') and ('_original' not in file_name) and ('_backup' not in file_name):
            uploadOneFile(arch_dir, 'platepars_all_recalibrated.json', s3, targf, '.json')
            uploadOneFile(arch_dir, dir_file, s3, targf, file_ext)
        if (file_ext == '.mp4') and ('FF_' in file_name):
            uploadOneFile(arch_dir, dir_file, s3, targf, file_ext)
        elif file_ext in ('.jpg', '.kml', '.cal', '.json', '.csv') and ('DETECTED' not in file_name) and ('CAPTURED' not in file_name): 
            uploadOneFile(arch_dir, dir_file, s3, targf, file_ext)
        elif dir_file == 'mask.bmp' or dir_file == 'flat.bmp' or dir_file == '.config':
            uploadOneFile(arch_dir, dir_file, s3, targf, file_ext)
    return


def manualUpload(targ_dir):
    """ Manually send the target folder to ukmon archive. 
    To invoke this function run *python uploadToArchive.py /path/to/target/folder*
    in a terminal window. 

    You can also use this to test connectivity by passing a single parameter "test".
    """
    if targ_dir == 'test':
        with open('/tmp/test.txt', 'w') as f:
            f.write('test')
        try:
            myloc = os.path.split(os.path.abspath(__file__))[0]
            filename = os.path.join(myloc, 'archive.key')
            with open(filename, 'r') as fin:
                key = fin.readline().split('=')[1].strip()
                secr = fin.readline().split('=')[1].strip()
                reg = fin.readline().split('=')[1].strip()
                targf = fin.readline().split('=')[1].strip()
            if targf[0] == '"':
                targf = targf[1:len(targf)-1]
            conn = boto3.Session(aws_access_key_id=key, aws_secret_access_key=secr) 
            s3 = conn.resource('s3', region_name=reg)
            s3.meta.client.upload_file('/tmp/test.txt', 'ukmon-shared', 'test.txt')
            key = {'Objects': []}
            key['Objects'] = [{'Key': 'test.txt'}]
            s3.meta.client.delete_objects(Bucket='ukmon-shared', Delete=key)
            print('test successful')
        except Exception:
            print('unable to upload to archive - check key information')
        os.remove('/tmp/test.txt')
    else:
        arch_dir = os.path.join(targ_dir)
        uploadToArchive(arch_dir)


if __name__ == '__main__':
    manualUpload(sys.argv[1])
