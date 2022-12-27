import os
import shutil
from crontab import CronTab

import time
import paramiko
import json
import tempfile
import RMS.ConfigReader as cr


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
    iter=cron.find_command('refreshTools.sh')
    found = False
    for i in iter:
        if i.is_enabled():
            found = True
    if found is False:
        print('adding refreshTools job')
        job = cron.new('sleep 60 && {}/refreshTools.sh > {}/logs/refreshTools.log 2>&1'.format(myloc, datadir))
        job.every_reboot()
        cron.write()
    iter=cron.find_command('liveMonitor.sh')
    found = False
    for i in iter:
        if i.is_enabled():
            found = True
    if found is False:
        print('adding livestream job')
        job = cron.new('sleep 3600 && {}/liveMonitor.sh >> {}/logs/ukmon-live.log 2>&1'.format(myloc, datadir))
        job.every_reboot()
        cron.write()
    return 


def addDesktopIcons(myloc, statid):
    """
    This function adds the desktop icons which are links to the ini file and refresh scripts
    """
    print('checking/adding desktop icons')
    if not os.path.isdir(os.path.expanduser('~/Desktop')):
        os.makedirs(os.path.expanduser('~/Desktop'))
    cfglnk = os.path.expanduser('~/Desktop/UKMON_config_{}.txt'.format(statid))
    if not os.path.isfile(cfglnk):
        os.symlink(os.path.join(myloc, 'ukmon.ini'), cfglnk)
    reflnk = os.path.expanduser('~/Desktop/refresh_UKMON_tools_{}.sh'.format(statid))
    if not os.path.isfile(reflnk):
        os.symlink(os.path.join(myloc, 'refreshTools.sh'), reflnk)
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
        except:
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
    except:
        print('unable to check platepar, will try next time')
    return 
