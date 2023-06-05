# Copyright (c) Mark McIntyre
# pytest tests for ukmon-pitools
# makes use of various RMS code

import os
import sys
import pytest
from ukmonPostProc import main


myloc = os.path.split(os.path.abspath(__file__))[0]
homedir = os.path.join(myloc, 'ukmpp')
tmpdir = os.path.join(myloc, 'output')
try:
    os.makedirs(tmpdir) # , exist_ok=Truee) exist_ok keyword not supported  with python7.2
except Exception:
    pass


def test_ukmonPostProcNoArgs():
    args=[None]
    ret = main(args)
    assert ret is False


@pytest.mark.skipif(sys.platform == 'win32', reason='test not valid on windows')
def test_ukmonPostProc1Arg():
    args=[None, os.path.join(myloc, 'ukmarch/sampledata/UK0006_20220914_185543_087124')]
    ret = main(args)
    assert ret is True


def test_ukmonPostProc1BadArg():
    args=[None, os.path.join(myloc, 'ukmarch/sampledata/UK0006_20220914_185543')]
    ret = main(args)
    assert ret is False


def test_ukmonPostProc2Args():
    args=[None, os.path.join(myloc, 'ukmarch/sampledata/UK0006_20220914_185543_087124'),
          os.path.join(myloc, 'ukmarch/sampledata/UK0006_20220914_185543_087124/.config')]
    ret = main(args)
    assert ret is True
