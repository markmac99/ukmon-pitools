#!/bin/bash
# Copyright (c) Mark McIntyre

# tests designed to run on a Pi 
here="$( cd "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
source ~/vRMS/bin/activate
export PYTHONPATH=$PYTHONPATH:${here}
[ -f ukmon.ini ] && cp ukmon.ini /tmp
[ -f live.key ] && cp live.key /tmp
[ -f domp4s ] && cp domp4s /tmp
if [ ! -d ~/source/testing ] ; then
    echo no test config, aborting
    exit
fi 
cp ~/source/testing/ukmon.ini . 
cp ~/source/testing/live.key .
touch ./domp4s
pytest -v ./tests --cov=. --cov-report=term-missing
rm ./live.key ./ukmon.ini ./domp4s
[ -f /tmp/ukmon.ini ] && mv /tmp/ukmon.ini .
[ -f /tmp/live.key ] && mv /tmp/live.key .
[ -f /tmp/domp4s ] && mv /tmp/live.key .
rm ./ukmarch/sampledata/UK0006_20220914_185543_087124/FF*.jpg
rm ./ukmarch/sampledata/UK0006_20220914_185543_087124/FF*.mp4