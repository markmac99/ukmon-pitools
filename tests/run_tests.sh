#!/bin/bash
# Copyright (c) Mark McIntyre

# tests designed to run on a Pi 
here="$( cd "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
source ~/vRMS/bin/activate
export PYTHONPATH=$PYTHONPATH:$(pwd)
cp ~/source/ukmon-pitools/ukmon.ini .
cp ~/source/ukmon-pitools/live.key .
pytest -v ./tests --cov=. --cov-report=term-missing
rm ./live.key ./ukmon.ini
