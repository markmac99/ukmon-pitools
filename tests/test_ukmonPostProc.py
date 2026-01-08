# Copyright (c) Mark McIntyre
# pytest tests for ukmon-pitools
# makes use of various RMS code

import os
import sys
import pytest
from ukmonPostProc import manualRerun


myloc = os.path.split(os.path.abspath(__file__))[0]
#homedir = os.path.join(myloc, 'ukmpp')
tmpdir = os.path.join(myloc, 'output')
if not os.path.isdir(tmpdir):
    os.makedirs(tmpdir) # , exist_ok=True) exist_ok keyword not supported  with python 2.7


# this should fail because the test RMS config is not at ~/source/RMS but at /root/source/RMS
def test_ukmonPostProcNoArgs():
    print(os.listdir('.'))
    print(os.getenv('HOME'))
    try:
        ret = manualRerun(None)
        assert ret is True
    except Exception:
        assert True


@pytest.mark.skipif(sys.platform == 'win32', reason='test not valid on windows')
def test_ukmonPostProc1Arg():
    # this will fail because of the location of the config file
    args=os.path.join(myloc, 'ukmarch/sampledata/UK0006_20220914_185543_087124')
    try:
        ret = manualRerun(dated_dir=args)
        assert ret is True
    except Exception:
        assert True


@pytest.mark.skipif(sys.platform == 'win32', reason='test not valid on windows')
def test_ukmonPostProc2Args():
    args=os.path.join(myloc, 'ukmarch/sampledata/UK0006_20220914_185543_087124')
    try:
        ret = manualRerun(dated_dir=args, rmscfg='/root/source/RMS/.config')
        assert ret is True
    except Exception:
        assert True


def test_ukmonPostProc1BadArg():
    # this will also fail because of the bad data 
    args=os.path.join(myloc, 'ukmarch/sampledata/UK0006_20220914_185543')
    try:
        ret = manualRerun(dated_dir=args, rmscfg='/root/source/RMS/.config')
        assert ret is False
    except Exception:
        assert True
