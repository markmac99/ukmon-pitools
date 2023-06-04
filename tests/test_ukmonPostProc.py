# Copyright (c) Mark McIntyre
# pytest tests for ukmon-pitools
# makes use of various RMS code

import os
import sys
from ukmonPostProc import main


myloc = os.path.split(os.path.abspath(__file__))[0]
homedir = os.path.join(myloc, 'ukmpp')
tmpdir = os.path.join(myloc, 'output')


def test_ukmonPostProcNoArgs():
    args=[None]
    ret = main(args)
    assert ret is False


def test_ukmonPostProc1Arg():
    args=[None, os.path.join(myloc, 'ukmarch/sampledata/UK0006_20220914_185543_087124')]
    if sys.platform == 'win32':
        print('test not valid on Windows')
        assert 1==1
    else:
        ret = main(args)
        assert ret is True


def test_ukmonPostProc2Args():
    args=[None, os.path.join(myloc, 'ukmarch/sampledata/UK0006_20220914_185543_087124'),
          os.path.join(myloc, 'ukmarch/sampledata/UK0006_20220914_185543_087124/.config')]
    ret = main(args)
    assert ret is True
