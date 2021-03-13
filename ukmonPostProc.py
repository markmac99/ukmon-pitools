# 
# python script thats called when the nightly run completes
#

import os
import sys
import shutil

import Utils.StackFFs as sff
import Utils.BatchFFtoImage as bff2i
import Utils.GenerateMP4s as gmp4
import Utils.GenerateTimelapse as gti
import RMS.ConfigReader as cr

import uploadToArchive 


def rmsExternal(cap_dir, arch_dir, config):
    rebootlockfile = os.path.join(config.data_dir, config.reboot_lock_file)
    with open(rebootlockfile, 'w') as f:
        f.write('1')

    # stack and create jpgs from the potential detections
    print('stacking the FF files')
    sff.stackFFs(arch_dir, 'jpg', filter_bright=True)
    bff2i.batchFFtoImage(arch_dir, 'jpg')

    # generate MP4s of detections
    print('generating MP4s')
    ftpdate=''
    if os.path.split(arch_dir)[1] == '':
        ftpdate=os.path.split(os.path.split(arch_dir)[0])[1]
    else:
        ftpdate=os.path.split(arch_dir)[1]
    ftpfile_name="FTPdetectinfo_"+ftpdate+'.txt'
    gmp4.generateMP4s(arch_dir, ftpfile_name)

    # generate an all-night timelapse and move it to arch_dir
    try: 
        print('generating a timelapse')
        gti.fps = 25
        gti.generateTimelapse(cap_dir, False)
        mp4name = os.path.basename(cap_dir) + '.mp4'
        shutil.move(os.path.join(cap_dir, mp4name), os.path.join(arch_dir, mp4name))
        
    except:
        errmsg = 'unable to create timelapse - maybe capture folder removed already'
        print(errmsg)

    uploadToArchive.uploadToArchive(arch_dir)

    os.remove(rebootlockfile)
    return


if __name__ == '__main__':
    hname = os.uname()[1]
    if len(sys.argv) < 1:
        if hname == 'meteorpi':
            cap_dir = '/home/pi/RMS_data/CapturedFiles/UK0006_20210130_172616_214463'
            arch_dir = '/home/pi/RMS_data/ArchivedFiles/UK0006_20210130_172616_214463'
        else:
            cap_dir = '/home/pi/RMS_data/CapturedFiles/UK000F_20210128_172253_791467'
            arch_dir = '/home/pi/RMS_data/ArchivedFiles/UK000F_20210128_172253_791467'
    else:
        cap_dir = os.path.join('/home/pi/RMS_data/CapturedFiles/', sys.argv[1])
        arch_dir = os.path.join('/home/pi/RMS_data/ArchivedFiles/', sys.argv[1])

    config = cr.parse(".config")

    rmsExternal(cap_dir, arch_dir, config)
