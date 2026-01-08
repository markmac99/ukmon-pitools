# Copyright (C) 2018-2023 Mark McIntyre

import os
import shutil
from crontab import CronTab
from subprocess import call
from git import remote, Repo

import time
import warnings
from cryptography.utils import CryptographyDeprecationWarning
with warnings.catch_warnings():
    warnings.filterwarnings('ignore', category=CryptographyDeprecationWarning)
    import paramiko

import json
import tempfile
import logging

import RMS.ConfigReader as cr
from RMS.Misc import isRaspberryPi
from uploadToArchive import readIniFile, updateHelperIp

log = logging.getLogger("ukmonlogger")
log.setLevel(logging.WARNING)

oldip = '3.9.65.98'
currip = '3.11.55.160'


def createDefaultIni(homedir, helperip='3.11.55.160', location='NOTCONFIGURED', stationid=''):
    """
    Create a default ini file, if its not present on the target
    """
    homedir = os.path.normpath(os.path.expanduser(homedir))
    rmscfg = '~/source/Stations/{}/.config'.format(stationid)
    if not os.path.isfile(os.path.expanduser(rmscfg)):
        rmscfg = '~/source/RMS/.config'
    
    keyfile = '~/.ssh/ukmon_{}'.format(stationid)
    with open(os.path.join(homedir, 'ukmon.ini'), 'w') as outf:
        outf.write("# config data for this station\n")
        outf.write("export LOCATION={}\n".format(location))
        outf.write("export UKMONHELPER={}\n".format(helperip))
        outf.write("export UKMONKEY={}\n".format(keyfile))
        outf.write("export RMSCFG={}\n".format(rmscfg))
        outf.write('export DOMP4s=1\n')
        outf.write('export MAGLIM=1\n')
    return True


def validateIni(homedir, newhelperip=None):
    """
    Check the ini file contains the required lines. 
    """
    homedir = os.path.expanduser(os.path.normpath(homedir))
    location = None
    keyfile = None
    rmscfg = None
    helperip = None
    if newhelperip is None:
        newhelperip = currip
    inifname = os.path.join(homedir, 'ukmon.ini')
    if os.path.isfile(inifname):
        inifdata = open(inifname, 'r').readlines()
        for li in inifdata:
            li = li.strip()
            if 'LOCATION' in li:
                location = li.split('=')[1]
            if 'UKMONKEY' in li:
                keyfile = li.split('=')[1]
            if 'RMSCFG' in li:
                rmscfg = li.split('=')[1]
            if 'UKMONHELPER' in li:
                helperip = li.split('=')[1]
    if location is None or keyfile is None or rmscfg is None or helperip is None:
        createDefaultIni(homedir, newhelperip, location, rmscfg)
    if helperip == oldip:
        updateHelperIp(homedir, newhelperip)
    updateMp4andMag(inifname, homedir)
    return True


def findLocationFromOldIni(stationid):
    inif = os.path.expanduser('~/source/ukmon-pitools-{}/ukmon.ini'.format(stationid))
    location = 'NOTCONFIGURED'
    if os.path.isfile(inif):
        flis = open(inif, 'r').readlines()
        loc = [x for x in flis if 'LOCA' in x]
        location = loc[0].strip().split('=')[1]
    return location    


def relocateGitRepo():
    myloc = os.path.split(os.path.abspath(__file__))[0]
    thisrepo = Repo(myloc)
    origin = thisrepo.remote('origin')
    if 'markmac99' in origin.url:
        origin.rename('upstream')
        remote.Remote.add(thisrepo, 'origin','https://github.com/ukmda/ukmon-pitools.git')
        cfg = thisrepo.heads.main.config_writer()
        cfg.set('remote','origin')
        cfg.release()
        cfg = thisrepo.heads.dev.config_writer()
        cfg.set('remote','origin')
        cfg.release()
        print('git remote updated')
    return 


def updateMp4andMag(inif, homedir):
    """
    Move the mp4 flag into the ini file and add the maglim flag if missing
    """
    domp4s = 0
    if open(inif, 'r').read()[-1] != '\n':
        open(inif, 'a').write('\n')
    if os.path.isfile(os.path.join(homedir, 'domp4s')):
        domp4s = 1
        os.remove(os.path.join(homedir, 'domp4s'))
    if 'DOMP4S' not in open(inif).read():
        open(inif,'a').write('export DOMP4S={}\n'.format(domp4s))
    if 'MAGLIM' not in open(inif).read():
        open(inif,'a').write('export MAGLIM=1\n')
    return


def installUkmonFeed(rmscfg='~/source/RMS/.config'):
    """ 
    Installs the UKMon postprocessing script into the RMS config file.
    It is called from the refreshTools script during initial installation and should never
    be called outside of that unless you're *certain* you know what you're doing. The script 
    alters the rms .config file. 

    """
    myloc = os.path.split(os.path.abspath(__file__))[0]
    cfgname = os.path.expanduser(rmscfg)
    config = cr.parse(cfgname)
    datadir = os.path.expanduser(config.data_dir)
    statid = config.stationID
    while statid == 'XX0001':
        print('RMS is refreshing, waiting 30s...')
        time.sleep(30)
        config = cr.parse(cfgname)
        statid = config.stationID

    checkPostProcSettings(myloc, cfgname)
    checkCrontab(myloc, datadir)
    addDesktopIcons(myloc, statid)
    checkPlatepar(myloc, statid, os.path.dirname(cfgname))
    return 


def checkPostProcSettings(myloc, cfgname):
    """
    Check that the RMS .config file contains the correct post-processing settings to run the ukmon process. 
    """
    print('checking postProcessing Settings')

    config = cr.parse(cfgname)
    scrname = os.path.join(myloc, 'ukmonPostProc.py')
    esr = config.external_script_run
    extl = os.path.expanduser(config.external_script_path)
    print(extl)
    if 'ukmonPostProc' not in extl or ('ukmonPostProc' in extl and myloc not in extl):
        if esr is True:
            if 'ukmonPostProc' not in extl:
                print('saving current external script details')
                with open(os.path.join(myloc, 'extrascript'), 'w') as outf:
                    outf.write(extl)
        print('updating RMS config file')
        with open(cfgname, 'r') as inf:
            lines = inf.readlines()
        _, tmpname = tempfile.mkstemp()
        with open(tmpname, 'w') as outf:
            for li in lines:
                if len(li) > 0 and li[0] != ';':
                    if 'auto_reprocess_external_script_run: ' in li:
                        li = 'auto_reprocess_external_script_run: true  \n'
                    if 'external_script_path: ' in li:
                        li = 'external_script_path: {}  \n'.format(scrname)
                    if 'external_script_run: ' in li and 'auto_reprocess_' not in li:
                        li = 'external_script_run: true  \n'
                    if 'auto_reprocess: ' in li:
                        li = 'auto_reprocess: true  \n'
                outf.write(li)
        _, cfgbase = os.path.split(cfgname)
        bkpcnf = os.path.join(myloc, cfgbase + '.backup')
        print('backing up RMS config to {}'.format(bkpcnf))
        shutil.copyfile(cfgname, bkpcnf)
        shutil.copyfile(tmpname, cfgname)
        try:
            os.remove(tmpname)
        except Exception:
            pass
    else:
        print('ukmonPostProc present')
    return     


def checkCrontab(myloc, datadir):
    """ 
    Add the crontab entries for the refresh job and live stream
    """
    print('checking crontab')
    cron = CronTab(user=True)
    for job in cron:
        if '{}/liveMonitor.sh'.format(myloc) in job.command or '{}/refreshTools.sh'.format(myloc) in job.command:
            cron.remove(job)
            cron.write()

    job = cron.new('sleep 120 && {}/refreshTools.sh > {}/logs/refreshTools.log 2>&1'.format(myloc, datadir))
    job.every_reboot()
    cron.write()

    job = cron.new('sleep 300 && {}/liveMonitor.sh >> /dev/null 2>&1'.format(myloc))
    job.every_reboot()
    cron.write()
    job = cron.new('{}/liveMonitor.sh >> /dev/null 2>&1'.format(myloc))
    job.setall(1, 12, '*', '*', '*')
    cron.write()
    return 


def createSystemdService(myloc, camid):
    """
    Create a systemd style service for the livestream, in user-space. 
    This should be more reliable than a cron job. 
    """
    unitname = os.path.expanduser('~/.config/systemd/user/ukmonlive-{}.service'.format(camid))
    if not os.path.isfile(unitname):
        with open(unitname,'w') as outf:
            outf.write('[Unit]\nDescription=UKMON Live stream service for {}\n'.format(camid))
            outf.write('After=network.target auditd.service\n\n')
            outf.write('[Service]\nExecStart={}/liveMonitor.sh\nRestart=always\n\n'.format(myloc))
            outf.write('[Install]\nWantedBy=multi-user.target\n\n')
            call(['systemctl','--user','daemon-reload'])
            call(['systemctl','--user','enable','ukmonlive-{}'.format(camid)])
            call(['systemctl','--user','start','ukmonlive-{}'.format(camid)])
    return 


def createUbuntuIcon(myloc):
    """
    Create Ubuntu-compatible desktop icons. 
    These different from the Debian-compatible ones normally used by RMS and 
    which dont work properly on Ubuntu.
    """
    reflnk = os.path.expanduser('~/Desktop/refresh_UKMON_tools.sh')
    if os.path.isfile(reflnk):
        os.remove(reflnk)
    reflnk = os.path.expanduser('~/Desktop/refresh_UKMON_tools.desktop')
    with open(reflnk, 'w') as outf:
        outf.write('[Desktop Entry]\n')
        outf.write('Name=refresh_UKMON_Tools\n')
        outf.write('Comment=Runs ukmon tools refresh\n')
        outf.write('Exec={}\n'.format(os.path.join(myloc, 'refreshTools.sh')))
        outf.write('Icon=\n')
        outf.write('Terminal=true\n')
        outf.write('Type=Application\n')
    cmdstr = 'gio set {} metadata::trusted true'.format(reflnk)
    call([cmdstr], shell=True)
    os.chmod(reflnk, 0o744)
    return 


def addDesktopIcons(myloc, statid):
    """
    For Debian and Raspian, add the desktop icons which are links to the ini file and refresh scripts
    """
    print('checking/adding desktop icons')
    if not os.path.isdir(os.path.expanduser('~/Desktop')):
        os.makedirs(os.path.expanduser('~/Desktop'))
    # the main and camera config files
    cfglnk = os.path.expanduser('~/Desktop/UKMON_config.txt')
    if not os.path.islink(cfglnk):
        os.symlink(os.path.join(myloc, 'ukmon.ini'), cfglnk)
    camlnk = os.path.expanduser('~/Desktop/UKMON_cameras.txt')
    if not os.path.islink(camlnk):
        os.symlink(os.path.join(myloc, 'cameras.ini'), camlnk)
    if isRaspberryPi():
        reflnk = os.path.expanduser('~/Desktop/refresh_UKMON_tools.sh')
        if not os.path.islink(reflnk):
            os.symlink(os.path.join(myloc, 'refreshTools.sh'), reflnk)
    else:
        createUbuntuIcon(myloc)
    return


def checkPlatepar(homedir, statid, rmsloc):
    """
    Check for a new platepar on the server and retrieves it if present.  
    The file is checked for compatability with the station.  
    """
    homedir = os.path.expanduser(os.path.normpath(homedir))
    inifvals = readIniFile(os.path.join(homedir, 'ukmon.ini'), statid)
    if not inifvals or inifvals['LOCATION']=='NOTCONFIGURED':
        return
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try: 
        pkey = paramiko.RSAKey.from_private_key_file(os.path.expanduser(inifvals['UKMONKEY'])) 
        ssh_client.connect(inifvals['UKMONHELPER'], username=inifvals['LOCATION'], pkey=pkey, look_for_keys=False)
        ftp_client = ssh_client.open_sftp()
        fetchpp = True
        try:
            ftp_client.get('platepar/platepar_cmn2010.cal','/tmp/platepar_cmn2010.cal')
        except Exception:
            fetchpp = False
        if fetchpp:
            print('Fetching new platepar...')
            js = json.load(open('/tmp/platepar_cmn2010.cal'))
            if js['station_code'] != statid:
                print('Station ID mismatch, not using new platepar')
            else:
                targpp = os.path.join(rmsloc, 'platepar_cmn2010.cal')
                shutil.copyfile('/tmp/platepar_cmn2010.cal', targpp)
                ftp_client.remove('platepar/platepar_cmn2010.cal')
        if os.path.isfile('/tmp/platepar_cmn2010.cal'):
            os.remove('/tmp/platepar_cmn2010.cal')
        ftp_client.close()
    except Exception:
        print('unable to check platepar, will try next time')
    ssh_client.close()
    return 
