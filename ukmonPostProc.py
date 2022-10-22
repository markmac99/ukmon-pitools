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
import logging
from RMS.Logger import initLogging

import uploadToArchive 

log = logging.getLogger("logger")


def installUkmonFeed(rmscfg='~/source/RMS/.config'):
    """ This function installs the UKMon postprocessing script into the RMS config file.
    It is called from the refreshTools script during initial installation and should never
    be called outside of that unless you're *certain* you know what you're doing. The script 
    alters the rms .config file. 

    """
    myloc = os.path.split(os.path.abspath(__file__))[0]
    newpath = os.path.join(myloc, 'ukmonPostProc.py')
    cfgname = os.path.expanduser(rmscfg)
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
    # called from RMS to trigger the UKMON specific code

    # clear existing log handlers
    log = logging.getLogger("logger")
    while len(log.handlers) > 0:
        log.removeHandler(log.handlers[0])
        
    initLogging(config, 'ukmon_')
    log.info('ukmon external script started')
    
    rebootlockfile = os.path.join(config.data_dir, config.reboot_lock_file)
    with open(rebootlockfile, 'w') as f:
        f.write('1')

    # stack and create jpgs from the potential detections
    log.info('stacking the FF files')
    sff.stackFFs(arch_dir, 'jpg', filter_bright=True, subavg=True)
    log.info('creating JPGs')
    try:
        bff2i.batchFFtoImage(arch_dir, 'jpg', True)
    except:
        bff2i.batchFFtoImage(arch_dir, 'jpg')

    myloc = os.path.split(os.path.abspath(__file__))[0]
    log.info('app home is {}'.format(myloc))
    try:
        f = open(os.path.join(myloc, 'domp4s'),'r') 
        f.close()
        # generate MP4s of detections
        log.info('generating MP4s')
        ftpdate=''
        if os.path.split(arch_dir)[1] == '':
            ftpdate=os.path.split(os.path.split(arch_dir)[0])[1]
        else:
            ftpdate=os.path.split(arch_dir)[1]
        ftpfile_name="FTPdetectinfo_"+ftpdate+'.txt'
        gmp4.generateMP4s(arch_dir, ftpfile_name)
    except Exception:
        log.info('mp4 creation not enabled')
    # generate an all-night timelapse and move it to arch_dir

    try:
        f = open(os.path.join(myloc, 'dotimelapse'),'r') 
        f.close()
        try: 
            log.info('generating a timelapse')
            gti.fps = 25
            gti.generateTimelapse(cap_dir, False)
            mp4name = os.path.basename(cap_dir) + '.mp4'
            shutil.move(os.path.join(cap_dir, mp4name), os.path.join(arch_dir, mp4name))
            
        except:
            log.info('unable to create timelapse - maybe capture folder removed already')
    except Exception:
        log.info('timelapse creation not enabled')

    log.info('uploading to archive')
    uploadToArchive.uploadToArchive(arch_dir)

    # do not remote reboot lock file if running another script
    # os.remove(rebootlockfile)
    log.info('about to test for extra script')
    try:
        with open(os.path.join(myloc, 'extrascript'),'r') as extraf:
            extrascript=extraf.readline().strip()

        log.info('running additional script {:s}'.format(extrascript))
        sloc, sname = os.path.split(extrascript)
        sys.path.append(sloc)
        scrname, _ = os.path.splitext(sname)
        nextscr=impmod(scrname)
        nextscr.rmsExternal(cap_dir, arch_dir, config)
    except (IOError,OSError):
        log.info('additional script not called')
        try:
            os.remove(rebootlockfile)
        except:
            log.info('unable to remove reboot lock file, pi will not reboot')
            pass

    # clear log handlers again
    while len(log.handlers) > 0:
        log.removeHandler(log.handlers[0])  
    return


def manualRerun(dated_dir):
    """This function is used to manually rerun the Ukmon post processing script. 
    To invoke this function, open a Terminal window and run the following:

    *python ../ukmon-pitools/ukmonPostProc.py dated_dir*

    Args:
        dated_dir (str): This is the name of the folder to upload eg UK000F_20210512_202826_913898
    """
    config = cr.parse(os.path.expanduser('~/source/RMS/.config'))
    cap_dir = os.path.join(config.data_dir, 'CapturedFiles', dated_dir)
    arch_dir = os.path.join(config.data_dir, 'ArchivedFiles', dated_dir)
    rmsExternal(cap_dir, arch_dir, config)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('usage: python ukmonPostProc.py arc_dir_name')
        print('eg python ukmonPostProc.py UK0006_20210312_183741_206154')
        print('\n nb: script must be run from RMS source folder')
    else:
        manualRerun(sys.argv[1])
