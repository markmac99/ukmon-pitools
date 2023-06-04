# Copyright (c) Mark McIntyre
# pytest tests for ukmon-pitools
# makes use of various RMS code

import os
#from liveMonitor import monitorLogFile # noqa:E402
#from RMS.ConfigReader import loadConfigFromDirectory # noqa:E402

myloc = os.path.split(os.path.abspath(__file__))[0]
homedir = os.path.join(myloc, 'ukml')
tmpdir = os.path.join(myloc, 'output')


def test_singleStation():
    rmscfg = os.path.join(myloc, 'lmtest', '.config')
    camloc = 'tackley_nw'
    print(rmscfg, camloc)
    #cfg = loadConfigFromDirectory('.config', os.path.join(myloc, 'ukml', 'lmtest'))
    #print(cfg.data_dir, os.getcwd())
    #os.makedirs(cfg.data_dir, exist_ok=True)
    #monitorLogFile(camloc, rmscfg)
    assert 1==1
