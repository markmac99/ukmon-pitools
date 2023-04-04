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

# Copyright (C) 2018-2023 Mark McIntyre


def createDefaultIni(homedir, helperip=None):
    rmscfg = '~/source/RMS/.config'
    keyfile = '~/.ssh/ukmon'
    homedir = os.path.normpath(homedir)
    camid = homedir[homedir.find('pitools')+8:]
    if camid != '':
        rmscfg = '~/source/Stations/{}/.config'.format(camid)
        keyfile = '~/.ssh/ukmon-{}'.format(camid)
    if helperip is None:
        helperip = '3.8.65.98'
    os.makedirs(homedir, exist_ok=True)
    with open(os.path.join(homedir, 'ukmon.ini'), 'w') as outf:
        outf.write("# config data for this station\n")
        outf.write("export LOCATION=NOTCONFIGURED\n")
        outf.write("export UKMONHELPER={}\n".format(helperip))
        outf.write("export UKMONKEY={}\n".format(keyfile))
        outf.write("export RMSCFG={}\n".format(rmscfg))
    return 


def updateHelperIp(homedir, helperip):
    homedir = os.path.normpath(homedir)
    lis = open(os.path.join(homedir, 'ukmon.ini'), 'r').readlines()
    with open(os.path.join(homedir, 'ukmon.ini'), 'w') as outf:
        for li in lis:
            if 'UKMONHELPER' in li:
                outf.write("export UKMONHELPER={}\n".format(helperip))
            else:
                outf.write('{}'.format(li))


def installUkmonFeed(rmscfg='~/source/RMS/.config'):
    """ This function installs the UKMon postprocessing script into the RMS config file.
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
        os.remove(tmpname)
    else:
        print('ukmonPostProc present')
    return     


def checkCrontab(myloc, datadir):
    """ This function adds the crontab entries
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
    This function adds the desktop icons which are links to the ini file and refresh scripts
    """
    print('checking/adding desktop icons')
    if not os.path.isdir(os.path.expanduser('~/Desktop')):
        os.makedirs(os.path.expanduser('~/Desktop'))
    cfglnk = os.path.expanduser('~/Desktop/UKMON_config_{}.txt'.format(statid))
    if not os.path.islink(cfglnk):
        os.symlink(os.path.join(myloc, 'ukmon.ini'), cfglnk)
    if isRaspberryPi is True:
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


def checkPlatepar(statid, rmsloc):
    idfile = os.path.expanduser(os.getenv('UKMONKEY'))
    svr = os.getenv('UKMONHELPER')
    usr = os.getenv('LOCATION')
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try: 
        ssh_client.connect(svr, username=usr, key_filename=idfile)
        ftp_client = ssh_client.open_sftp()
        fetchpp = True
        try:
            ftp_client.get('platepar/platepar_cmn2010.cal','/tmp/platepar_cmn2010.cal')
        except Exception:
            print('unable to fetch new platepar')
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
