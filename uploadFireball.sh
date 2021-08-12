#!/bin/bash
source ~/vRMS/bin/activate
here="$( cd "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
source $here/ukmon.ini

cd ~/source/RMS
export PYTHONPATH=/home/pi/source/ukmon-pitools
python << EOD
import uploadToArchive as ua
import sys
if len(sys.argv) < 1: 
    print('usage: ./uploadFireball.sh FF_filename.fits')
else:
    ua.fireballUpload(sys.argv[1])
EOD