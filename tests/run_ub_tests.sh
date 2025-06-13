#!/bin/bash
# Copyright (c) Mark McIntyre

# tests designed to run on ubuntu
here="$( cd "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
if [ ! -f /keys/ukmon.ini ] ; then
    echo no test config, aborting
    exit
fi 
cp /keys/ukmon.ini . 
cp /keys/live.key .
pushd /root/source/RMS 
git stash && git pull && git stash apply 
cp /keys/.config /root/source/RMS/
popd
touch ./domp4s
source ukmon.ini
echo testing for $LOCATION
pip install -r ./requirements.txt
pip install --upgrade ruff pytest xmltodict pytest-cov 
export PYTHONPATH=$PYTHONPATH:/root/source/RMS:${here}/..
cd /root/source/RMS
ls -ltra .config
pwd
pytest -v $here/ --cov=$here/../ --cov-report=term-missing --cov-config=$here/../.coveragerc_lnx 
