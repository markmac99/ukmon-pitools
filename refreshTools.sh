#!/bin/bash

# refresh ukmon-pitools
# Copyright (C) 2018- Mark McIntyre

myself=$(readlink -f $0)
here="$( cd "$(dirname "$myself")" >/dev/null 2>&1 ; pwd -P )"
cd $here

export PYTHONPATH=$here:~/source/RMS
source ~/vRMS/bin/activate

echo "checking required python libs are installed"
pip list | grep boto3 || pip install boto3 
# python-crontab v2.5.1 for python 2.7 backwards compatability. Sigh. 
pip list | grep python-crontab | grep 2.5.1 || pip install python-crontab==2.5.1
pip list | grep paramiko || pip install paramiko

# validate the ini file 
echo "checking ini file is valid"
python -c "import ukmonInstaller as pp ; pp.validateIni('${here}', '3.11.55.160');"
source $here/ukmon.ini

echo "refreshing toolset"
git config pull.ff only 
git stash 
git pull
git stash apply

python -c "from ukmonInstaller import relocateGitRepo;relocateGitRepo()"
git fetch

echo "testing connections"
python $here/sendToLive.py test test
python $here/uploadToArchive.py test
echo "if you did not see two success messages contact us for advice" 
