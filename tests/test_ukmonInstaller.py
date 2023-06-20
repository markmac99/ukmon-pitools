# tests for ukmonInstaller

import os
import shutil


from ukmonInstaller import createDefaultIni, updateHelperIp, updateLocation, \
    checkPostProcSettings, validateIni, getLatestKeys # noqa: E402
myloc = os.path.split(os.path.abspath(__file__))[0]
homedir = os.path.join(myloc, 'ukminst')
tmpdir = os.path.join(myloc, 'output')
if not os.path.isdir(tmpdir):
    os.makedirs(tmpdir) # , exist_ok=Truee) exist_ok keyword not supported  with python7.2


def test_createDefaultIni():
    createDefaultIni(tmpdir)
    lis = open(os.path.join(tmpdir,'ukmon.ini'), 'r').readlines()
    for li in lis:
        if 'RMSCFG' in li:
            assert li == 'export RMSCFG=~/source/RMS/.config\n'
            os.remove(os.path.join(tmpdir,'ukmon.ini'))
            return 


def test_validateIni():
    validateIni(tmpdir)
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


def test_getLatestKeys_normal():
    if not os.path.isfile(os.path.join(homedir, 'ukmon.ini')):
        shutil.copyfile(os.path.join(myloc, '../ukmon.ini'),os.path.join(homedir,'ukmon.ini'))
    res = getLatestKeys(homedir)
    assert res is True
    os.remove(os.path.join(homedir, 'ukmon.ini'))
    return 


def test_getLatestKeys_newname():
    if not os.path.isfile(os.path.join(homedir, 'ukmon.ini')):
        shutil.copyfile(os.path.join(myloc, '../ukmon.ini'),os.path.join(homedir,'ukmon.ini'))
    remoteinifname = 'ukmon.ini.newname'
    res = getLatestKeys(homedir, remoteinifname=remoteinifname)
    assert res is True
    lis = open(os.path.join(homedir, 'ukmon.ini'), 'r').readlines()
    for li in lis:
        li = li.strip()
        if 'LOCATION' in li:
            assert li.split('=')[1] == 'newloc'
    os.remove(os.path.join(homedir, 'ukmon.ini'))
    return


def test_getLatestKeys_newip():
    if not os.path.isfile(os.path.join(homedir, 'ukmon.ini')):
        shutil.copyfile(os.path.join(myloc, '../ukmon.ini'),os.path.join(homedir,'ukmon.ini'))
    remoteinifname = 'ukmon.ini.newip'
    res = getLatestKeys(homedir, remoteinifname=remoteinifname)
    assert res is True
    lis = open(os.path.join(homedir, 'ukmon.ini'), 'r').readlines()
    for li in lis:
        li = li.strip()
        if 'UKMONHELPER' in li:
            assert li.split('=')[1] == '1.2.3.4'
    #os.remove(os.path.join(homedir, 'ukmon.ini'))
    return
