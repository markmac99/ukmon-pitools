# Copyright (C) 2018-2023 Mark McIntyre

import os
import shutil
from crontab import CronTab
from subprocess import call

import time
import paramiko
import json
import tempfile
import RMS.ConfigReader as cr
from RMS.Misc import isRaspberryPi
from uploadToArchive import readKeyFile

oldip = '3.9.65.98'
currip = '3.11.55.160'


def createDefaultIni(homedir, helperip='3.11.55.160', location='NOTCONFIGURED', keyfile=None, rmscfg=None):
    """
    Create a default ini file, if its not present on the target
    """
    homedir = os.path.normpath(os.path.expanduser(homedir))
    if not os.path.isdir(homedir):
        os.makedirs(homedir)
    camid = homedir[homedir.find('pitools')+8:]
    if rmscfg is None:
        if camid != '' and 'tests' not in camid:
            rmscfg = '~/source/Stations/{}/.config'.format(camid)
        else:
            rmscfg = '~/source/RMS/.config'
    if keyfile is None:
        if camid != '' and 'tests' not in camid:
            keyfile = '~/.ssh/ukmon-{}'.format(camid)
        else:
            keyfile = '~/.ssh/ukmon'
    if helperip is None:
        helperip = currip
    if location is None:
        location = 'NOTCONFIGURED'
    with open(os.path.join(homedir, 'ukmon.ini'), 'w') as outf:
        outf.write("# config data for this station\n")
        outf.write("export LOCATION={}\n".format(location))
        outf.write("export UKMONHELPER={}\n".format(helperip))
        outf.write("export UKMONKEY={}\n".format(keyfile))
        outf.write("export RMSCFG={}\n".format(rmscfg))
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
        createDefaultIni(homedir, newhelperip, location, keyfile, rmscfg)
    if helperip == oldip:
        updateHelperIp(homedir, newhelperip)
    return True


def updateHelperIp(homedir, helperip):
    """
    Update the ukmon.ini file with a new IP address if neeeded. 
    """
    homedir = os.path.normpath(homedir)
    lis = open(os.path.join(homedir, 'ukmon.ini'), 'r').readlines()
    with open(os.path.join(homedir, 'ukmon.ini'), 'w') as outf:
        for li in lis:
            if 'UKMONHELPER' in li:
                outf.write("export UKMONHELPER={}\n".format(helperip))
            else:
                outf.write('{}'.format(li))


def updateLocation(homedir, newloc):
    """
    Update the ukmon-specific location, if a new one was supplied. Allows us to move cameras to new sites. 
    """
    homedir = os.path.normpath(homedir)
    lis = open(os.path.join(homedir, 'ukmon.ini'), 'r').readlines()
    with open(os.path.join(homedir, 'ukmon.ini'), 'w') as outf:
        for li in lis:
            if 'LOCATION' in li:
                outf.write("export LOCATION={}\n".format(newloc))
            else:
                outf.write('{}'.format(li))
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
    checkPlatepar(statid, os.path.dirname(cfgname))
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

    job = cron.new('sleep 60 && {}/refreshTools.sh > {}/logs/refreshTools.log 2>&1'.format(myloc, datadir))
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


def createUbuntuIcon(myloc, statid):
    """
    Create Ubuntu-compatible desktop icons. 
    These different from the Debian-compatible ones normally used by RMS and 
    which dont work properly on Ubuntu.
    """
    reflnk = os.path.expanduser('~/Desktop/refresh_UKMON_tools_{}.sh'.format(statid))
    if os.path.isfile(reflnk):
        os.remove(reflnk)
    reflnk = os.path.expanduser('~/Desktop/refresh_UKMON_tools_{}.desktop'.format(statid))
    with open(reflnk, 'w') as outf:
        outf.write('[Desktop Entry]\n')
        outf.write('Name=refresh_UKMON_Tools_{}\n'.format(statid))
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
    cfglnk = os.path.expanduser('~/Desktop/UKMON_config_{}.txt'.format(statid))
    if not os.path.islink(cfglnk):
        os.symlink(os.path.join(myloc, 'ukmon.ini'), cfglnk)
    if isRaspberryPi():
        reflnk = os.path.expanduser('~/Desktop/refresh_UKMON_tools_{}.sh'.format(statid))
        if not os.path.islink(reflnk):
            os.symlink(os.path.join(myloc, 'refreshTools.sh'), reflnk)
    else:
        createUbuntuIcon(myloc, statid)
    # remove bad links if present
    cfglnk = os.path.expanduser('~/Desktop/UKMON_config_XX0001.txt')
    if os.path.islink(cfglnk):
        os.unlink(cfglnk)
    reflnk = os.path.expanduser('~/Desktop/refresh_UKMON_tools_XX0001.sh')
    if os.path.islink(reflnk):
        os.unlink(reflnk)
    return


def getLatestKeys(homedir, remoteinifname='ukmon.ini'):
    """
    Retrieve the latest ini and key files from the ukmon server.  
    If the ini file contains a new server IP or new location, the local copy of the 
    ini file is updated accordingly.  
    """
    homedir = os.path.expanduser(os.path.normpath(homedir))
    inifvals = readKeyFile(os.path.join(homedir, 'ukmon.ini'))
    idfile = os.path.expanduser(inifvals['UKMONKEY'])
    svr = inifvals['UKMONHELPER']
    usr = inifvals['LOCATION']
    print(idfile, svr, usr)
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    #try: 
    if True:
        pkey = paramiko.RSAKey.from_private_key_file(idfile) 
        ssh_client.connect(svr, username=usr, pkey=pkey, look_for_keys=False)
        ftp_client = ssh_client.open_sftp()

        # get the aws key file
        ftp_client.get('live.key', os.path.join(homedir, 'live.key'))
        os.chmod(os.path.join(homedir, 'live.key'), 0o600)

        # get the new ini and check for changes
        currinif = os.path.join(homedir, 'ukmon.ini')
        newinif = os.path.join(homedir, '.ukmon.new')
        ftp_client.put(currinif,'ukmon.ini.client')
        ftp_client.get(remoteinifname, newinif)
        iniflines = open(newinif,'r').readlines()
        for li in iniflines:
            li = li.strip()
            if 'UKMONHELPER' in li:
                newhelper = li.split('=')[1]
                if newhelper != svr:
                    updateHelperIp(homedir, newhelper)
                    print('server address updated')
            if 'LOCATION' in li:
                newloc = li.split('=')[1]
                if newloc != usr:
                    updateLocation(homedir, newloc)
                    print('location updated')
        os.remove(newinif)
        return True
    #except:
    else:
        return False


def checkPlatepar(statid, rmsloc):
    """
    Check for a new platepar on the server and retrieves it if present.  
    The file is checked for compatability with the station.  
    """
    idfile = os.path.expanduser(os.getenv('UKMONKEY').strip())
    svr = os.getenv('UKMONHELPER').strip()
    usr = os.getenv('LOCATION').strip()
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try: 
        pkey = paramiko.RSAKey.from_private_key_file(idfile) 
        ssh_client.connect(svr, username=usr, pkey=pkey, look_for_keys=False)
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
    return 
