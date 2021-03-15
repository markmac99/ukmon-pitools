import time
import os
import sys
import Utils.BatchFFtoImage as bff
import boto3


def follow(thefile):
    '''generator function that yields new lines in a file
    '''
    # seek the end of the file
    thefile.seek(0, os.SEEK_END)
    
    # start infinite loop
    while True:
        # read last line of file
        line = thefile.readline()
        # sleep if file hasn't been updated
        if not line:
            time.sleep(0.1)
            continue
            
        yield line 


def uploadOneEvent(capdir, ffname, camloc, outdir):
    outf.write('{:s} {:s} {:s}\n'.format(capdir, ffname, camloc))

    return


if __name__ == '__main__':
    outf = open('~/RMS_data/logs/liveMonitor.log', 'w')
    logfile = open(sys.argv[1],"r")
    camloc = sys.argv[2]
    capdir = ''
    loglines = follow(logfile)
    # iterate over the generator
    for line in loglines:
        if "Data directory" in line: 
            capdir = line.split(' ')[5]
            outf.write('{:s}\n'.format(line))

        if "detected meteors" in line and ": 0" not in line:
            if capdir != '':
                ffname = line.split(' ')[3]
                uploadOneEvent(capdir, ffname, camloc, outf)

    outf.close()
