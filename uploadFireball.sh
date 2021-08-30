#!/bin/bash
source ~/vRMS/bin/activate
here="$( cd "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
source $here/ukmon.ini

cd ~/source/RMS
export PYTHONPATH=~/source/ukmon-pitools
if [ "$1" == "" ] ; then
    echo usage ./uploadFireball.sh FF_name.fits
    exit 0
fi 
python << EOD
import uploadToArchive as ua
ua.fireballUpload("${1}")
EOD