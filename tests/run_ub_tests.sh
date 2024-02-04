#!/bin/bash
# Copyright (c) Mark McIntyre

# tests designed to run on a Pi 
here="$( cd "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
export PYTHONPATH=$PYTHONPATH:${here}
if [ ! -f /keys/ukmon.ini ] ; then
    echo no test config, aborting
    exit
fi 
cp /keys/.config /source/RMS/
cp /keys/ukmon.ini . 
cp /keys/live.key .
touch ./domp4s
source ukmon.ini
pytest -v ./tests/ --cov=./ --cov-report=term-missing --cov-config=.coveragerc_lnx 
