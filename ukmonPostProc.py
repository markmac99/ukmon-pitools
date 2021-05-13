# 
# python script thats called when the nightly run completes to generate jpgs 
# and upload data to the ukmeteornetwork
#
# Notes: 
# - to enable MP4 creation of each detection, create a file 'domp4s' in the same folder as this script
# - to enable creation of an all-night timelapse, create a file 'dotimelapse'
# - to trigger another python script after this one, create a file 'extrascript' containing the full path 
#   to the extra script. The script will be passed the same arguments as this one (cap_dir, arc_dir, config)

import os
import sys
import shutil

import Utils.StackFFs as sff
import Utils.BatchFFtoImage as bff2i
import Utils.GenerateMP4s as gmp4
import Utils.GenerateTimelapse as gti
import RMS.ConfigReader as cr

from importlib import import_module as impmod

import uploadToArchive 


def installUkmonFeed():
    """ Installs the UKMon postprocessing script into the RMS config file

    """
    myloc = os.path.split(os.path.abspath(__file__))[0]
    newpath = os.path.join(myloc, 'ukmonPostProc.py')
    cfgname = '/home/pi/source/RMS/.config'
    config = cr.parse(cfgname)
    esr = config.external_script_run
    extl = config.external_script_path

    print('checking parameters')
    if esr is True:
        if extl != newpath:
            print('saving current external script details')
            with open(os.path.join(myloc, 'extrascript'), 'w') as outf:
                outf.write(extl)

    print('updating RMS config file')
    with open(cfgname, 'r') as inf:
        lines = inf.readlines()
        with open('/tmp/new.config', 'w') as outf:
            for li in range(len(lines)):
                if 'auto_reprocess_external_script_run: ' in lines[li]:
                    lines[li] = 'auto_reprocess_external_script_run: true  \n'
                if 'external_script_path: ' in lines[li]:
                    lines[li] = 'external_script_path: {}  \n'.format(newpath)
                if 'external_script_run: ' in lines[li] and 'auto_reprocess_' not in lines[li]:
                    lines[li] = 'external_script_run: true  \n'
                if 'auto_reprocess: ' in lines[li]:
                    lines[li] = 'auto_reprocess: true  \n'
            outf.writelines(lines)
    _, cfgbase = os.path.split(cfgname)
    bkpcnf = os.path.join(myloc, cfgbase + '.backup')
    print('backing up RMS config to {}'.format(bkpcnf))
    shutil.copyfile(cfgname, bkpcnf)
    shutil.copyfile('/tmp/new.config', cfgname)

    return 


def rmsExternal(cap_dir, arch_dir, config):
    """Function called by RMS upon completion of data processing.

    Args:
        cap_dir (str): full path to the nightly capturedfiles directory
        arch_dir (str): full path to the nightly archivedfiles directory
        config (obj): RMS configuration object 
    """
    rebootlockfile = os.path.join(config.data_dir, config.reboot_lock_file)
    with open(rebootlockfile, 'w') as f:
        f.write('1')

    # stack and create jpgs from the potential detections
    print('stacking the FF files')
    sff.stackFFs(arch_dir, 'jpg', filter_bright=True)
    try:
        bff2i.batchFFtoImage(arch_dir, 'jpg', True)
    except:
        bff2i.batchFFtoImage(arch_dir, 'jpg')

    myloc = os.path.split(os.path.abspath(__file__))[0]
    try:
        f = open(os.path.join(myloc, 'domp4s'),'r') 
        f.close()
        # generate MP4s of detections
        print('generating MP4s')
        ftpdate=''
        if os.path.split(arch_dir)[1] == '':
            ftpdate=os.path.split(os.path.split(arch_dir)[0])[1]
        else:
            ftpdate=os.path.split(arch_dir)[1]
        ftpfile_name="FTPdetectinfo_"+ftpdate+'.txt'
        gmp4.generateMP4s(arch_dir, ftpfile_name)
    except Exception:
        print('mp4 creation not enabled')
    # generate an all-night timelapse and move it to arch_dir

    try:
        f = open(os.path.join(myloc, 'dotimelapse'),'r') 
        f.close()
        try: 
            print('generating a timelapse')
            gti.fps = 25
            gti.generateTimelapse(cap_dir, False)
            mp4name = os.path.basename(cap_dir) + '.mp4'
            shutil.move(os.path.join(cap_dir, mp4name), os.path.join(arch_dir, mp4name))
            
        except:
            errmsg = 'unable to create timelapse - maybe capture folder removed already'
            print(errmsg)
    except Exception:
        print('timelapse creation not enabled')

    uploadToArchive.uploadToArchive(arch_dir)

    os.remove(rebootlockfile)

    try:
        with open(os.path.join(myloc, 'extrascript'),'r') as extraf:
            extrascript=extraf.readline().strip()

        print('running additional script {:s}'.format(extrascript))
        sloc, sname = os.path.split(extrascript)
        sys.path.append(sloc)
        scrname, _ = os.path.splitext(sname)
        nextscr=impmod(scrname)
        nextscr.rmsExternal(cap_dir, arch_dir, config)
    except OSError:
        print('additional script not called')
        try:
            os.remove(rebootlockfile)
        except:
            pass
    
    return


def manualRerun(dated_dir):
    """Manually rerun the Ukmon post processing script 

    Note that this script *must* be run from the RMS source folder.

    Args:
        dated_dir (str): dated directory to upload eg UK000F_20210512_202826_913898
    """
    cap_dir = os.path.join('/home/pi/RMS_data/CapturedFiles', dated_dir)
    arch_dir = os.path.join('/home/pi/RMS_data/ArchivedFiles', dated_dir)
    config = cr.parse(".config")
    rmsExternal(cap_dir, arch_dir, config)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('usage: python ukmonPostProc.py arc_dir_name')
        print('eg python ukmonPostProc.py UK0006_20210312_183741_206154')
        print('\n nb: script must be run from RMS source folder')
    else:
        manualRerun(sys.argv[1])
