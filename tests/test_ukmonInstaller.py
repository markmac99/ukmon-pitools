# tests for ukmonInstaller

import os
import shutil


from ukmonInstaller import createDefaultIni, updateHelperIp, updateLocation, checkPostProcSettings # noqa: E402
myloc = os.path.split(os.path.abspath(__file__))[0]
homedir = os.path.join(myloc, 'ukminst')
tmpdir = os.path.join(myloc, 'output')
os.makedirs(homedir, exist_ok=True)
os.makedirs(tmpdir, exist_ok=True)


def test_createDefaultIni():
    createDefaultIni(tmpdir)
    lis = open(os.path.join(tmpdir,'ukmon.ini'), 'r').readlines()
    for li in lis:
        if 'RMSCFG' in li:
            assert li == 'export RMSCFG=~/source/RMS/.config\n'
            os.remove(os.path.join(tmpdir,'ukmon.ini'))
            return 


def test_updateHelperIp():
    createDefaultIni(tmpdir)
    updateHelperIp(tmpdir, '1.1.1.1')
    lis = open(os.path.join(tmpdir,'ukmon.ini'), 'r').readlines()
    for li in lis:
        if 'UKMONHELPER' in li:
            assert li == 'export UKMONHELPER=1.1.1.1\n'
            os.remove(os.path.join(tmpdir,'ukmon.ini'))
            return 
    

def test_updateLocation():
    createDefaultIni(tmpdir)
    updateLocation(tmpdir, 'plinkshire_w')
    lis = open(os.path.join(tmpdir,'ukmon.ini'), 'r').readlines()
    for li in lis:
        if 'LOCATION' in li:
            assert li == 'export LOCATION=plinkshire_w\n'
            os.remove(os.path.join(tmpdir,'ukmon.ini'))
            return 


def test_checkPostProcSettings():
    origcfg = os.path.join(homedir, '.config.orig')
    rmscfg = os.path.join(homedir, '.config')
    shutil.copyfile(origcfg, rmscfg)
    checkPostProcSettings(homedir, rmscfg)
    scrname = os.path.join(homedir, 'ukmonPostProc.py')
    lis = open(rmscfg, 'r').readlines()
    for li in lis:
        if 'auto_reprocess_external_script_run: ' in li:
            assert li == 'auto_reprocess_external_script_run: true  \n'
        if 'external_script_path: ' in li:
            assert li == 'external_script_path: {}  \n'.format(scrname)
        if 'external_script_run: ' in li and 'auto_reprocess_' not in li:
            assert li == 'external_script_run: true  \n'
        if 'auto_reprocess: ' in li:
            assert li == 'auto_reprocess: true  \n'
    os.remove(rmscfg)            
    return
