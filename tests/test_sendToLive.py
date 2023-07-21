# Copyright (c) Mark McIntyre
# pytest tests for ukmon-pitools
# makes use of various RMS code

import os
import sendToLive # noqa:E402
from RMS.ConfigReader import loadConfigFromDirectory # noqa:E402
import xmltodict # noqa:E402


basedir = os.path.realpath(os.path.dirname(__file__))
tmpdir = os.path.join(basedir, 'output')
if not os.path.isdir(tmpdir):
    os.makedirs(tmpdir)


def test_xmlcreatorName(dir_file = 'FF_UK001L_20230319_031241_804_0598784.fits',
                        expectedname='M20230319_031241_tackley_ne_UK001L.xml', srcdir='ukml/pi/uk001l',
                        camloc = 'tackley_ne'):
    cap_dir = os.path.join(basedir, srcdir)
    cfg = loadConfigFromDirectory('.config', cap_dir)
    fullxml, xmlname = sendToLive.createXMLfile(tmpdir, cap_dir, dir_file, camloc, cfg)
    assert xmlname == expectedname


def test_xmlData(xmlfile='M20230319_031241_tackley_ne_UK001L.xml', testval=47092310):
    fullxml = os.path.join(basedir, 'output', xmlfile)
    with open(fullxml) as fd:
        dd = xmltodict.parse(fd.read())
    uc = dd['ufocapture_record']['ufocapture_paths']        
    bri = int(uc['uc_path'][0]['@bmax'])
    os.remove(fullxml)
    assert bri==testval


def test_xmlUK008t():
    dir_file = 'FF_UK008T_20230213_025907_432_0828928.fits'
    expname = 'M20230213_025907_storrington_se_UK008T.xml'
    srcdir='ukml/pi/uk008t'
    camloc='storrington_se'
    test_xmlcreatorName(dir_file, expname, srcdir, camloc)


def test_uk008tData():
    test_xmlData(xmlfile='M20230213_025907_storrington_se_UK008T.xml', testval=84707799)


def test_xmlUK008tV2():
    dir_file = 'FF_UK008T_20230213_025917_665_0829184.fits'
    expname = 'M20230213_025917_storrington_se_UK008T.xml'
    srcdir='ukml/pi/uk008t'
    camloc='storrington_se'
    test_xmlcreatorName(dir_file, expname, srcdir, camloc)


def test_uk008tDataV2():
    test_xmlData(xmlfile='M20230213_025917_storrington_se_UK008T.xml', testval=234177206)


def test_xmlUK0045():
    dir_file = 'FF_UK0045_20230213_025919_082_0831744.fits'
    expname = 'M20230213_025919_redhill_e_UK0045.xml'
    srcdir='ukml/pi/uk0045'
    camloc='redhill_e'
    test_xmlcreatorName(dir_file, expname, srcdir, camloc)


def test_uk0045Data():
    test_xmlData(xmlfile='M20230213_025919_redhill_e_UK0045.xml', testval=233153959)


def test_createJpg():
    dir_file = 'FF_UK0045_20230213_025919_082_0831744.fits'
    expname = 'M20230213_025919_redhill_e_UK0045P.jpg'
    srcdir='ukml/pi/uk0045'
    camloc='redhill_e'
    cap_dir = os.path.join(basedir, srcdir)
    _, njpgname = sendToLive.createJpg(tmpdir, cap_dir, dir_file, camloc)
    os.remove(os.path.join(tmpdir, dir_file))
    os.remove(os.path.join(tmpdir, njpgname))
    assert njpgname == expname


def test_upload():
    retmsg = sendToLive.singleUpload('test','test')
    assert 'successful' in retmsg
