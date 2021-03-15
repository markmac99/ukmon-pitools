import time
import os
import sys
import Utils.BatchFFtoImage as bff
import boto3
import shutil
import tempfile



def uploadOneEvent(cap_dir, dir_file, camloc, outf, s3):
    target = 'ukmon-live'
    spls = dir_file.split('_')
    camid = spls[1]
    ymd = spls[2]
    hms = spls[3]
    micros = spls[4]
    yr = ymd[:4]
    mth = ymd[4:6]
    dy = ymd[6:8]
    hr = hms[:2]
    mi = hms[2:4]
    se = hms[4:6]
    se = se + '.{.2f}'.format(float(micros)/1000000)
    tmpdir = tempfile.mkdtemp()
    shutil.copy2(os.path.join(cap_dir, dir_file), tmpdir)
    bff.batchFFtoImage(tmpdir, 'jpg')
    file_name, _ = os.path.splitext(dir_file)
    ojpgname = file_name + '.jpg'
    njpgname = 'M' + ymd + '_' + hms + '_' + camloc + '_' + camid + 'P.jpg'
    fulljpg = os.path.join(cap_dir, njpgname)
    os.rename(os.path.join(cap_dir, ojpgname), fulljpg)

    xmlname = 'M' + ymd + '_' + hms + '_' + camloc + '_' + camid + '.xml'
    fullxml = os.path.join(cap_dir, xmlname)
    with open(fullxml, 'w') as ofl:
        ofl.write('<?xml version="1.0" encoding="UTF-8" ?>\n')
        ofl.write('<ufocapture_record version="215"')
        ofl.write('y="{:s}" mo="{:s}" d="{:s}" h="{:s}" m="{:s}" s="{:s}" ',format(yr, mth, dy, hr, mi, se))
        ofl.write('trig="1" frames="68" lng="LNG" lat="LAT" alt="ALTI" ')
        ofl.write('tz="0" u2="224" cx="720" cy="576" fps="25.000" head="30" ')
        ofl.write('tail="30" diff="2" sipos="6" sisize="15" dlev="40" dsize="4" ')
        ofl.write('lid="{:s}" observer="" sid="{:s}" cam="{:s}" lens="" cap="" '.format(camloc, camid, camid))
        ofl.write('comment="" interlace="1" bbf="0" dropframe="0">\n')
        ofl.write('    <ufocapture_paths hit="3">\n')
        ofl.write('     <uc_path fno="30" ono="18" pixel="3" bmax="79" x="395.7" y="282.3"></uc_path>\n')
        ofl.write('     <uc_path fno="30" ono="18" pixel="9" bmax="96" x="393.6" y="288.1"></uc_path>\n')
        ofl.write('     <uc_path fno="31" ono="18" pixel="16" bmax="112" x="391.1" y="295.5"></uc_path>\n')
        ofl.write('    </ufocapture_paths>\n')
        ofl.write('</ufocapture_record>\n')

    s3.meta.client.upload_file(fulljpg, target, njpgname, ExtraArgs={'ContentType': 'image/jpeg'})
    s3.meta.client.upload_file(fullxml, target, xmlname, ExtraArgs={'ContentType': 'application/xml'})
    print(njpgname)
    outf.write('{:s\n}'.format(njpgname))
    shutil.rmtree(tmpdir)
    return


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


if __name__ == '__main__':
    outf = open('~/RMS_data/logs/liveMonitor.log', 'w')
    logfile = open(sys.argv[1],"r")
    camloc = sys.argv[2]
    capdir = ''
    conn = boto3.Session() 
    s3 = conn.resource('s3')

    loglines = follow(logfile)
    # iterate over the generator
    for line in loglines:
        if "Data directory" in line: 
            capdir = line.split(' ')[5]
            outf.write('{:s}\n'.format(line))

        if "detected meteors" in line and ": 0" not in line:
            if capdir != '':
                ffname = line.split(' ')[3]
                uploadOneEvent(capdir, ffname, camloc, outf, s3)

    outf.close()
