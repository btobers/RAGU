# RAGU - Radar Analysis Graphical Utility
#
# copyright © 2020 btobers <tobers.brandon@gmail.com>
#
# distributed under terms of the GNU GPL3.0 license
"""
ingest_pulseekko is a module developed to ingest Sensors & Software pulseEKKO GPR data
adapted from ImpDAR/lib/load/load_pulse_ekko.py - David Lilien
"""
### imports ###
from radar import radar
from nav import navparse
import os,sys,struct,datetime
import numpy as np

class TraceHeaders:
    """Class used internally to handle pulse-ekko headers."""

    def __init__(self, tnum):
        """Create a container for all the trace headers."""
        self.header_index = 0
        self.trace_numbers = np.zeros((1, tnum))
        self.positions = np.zeros((1, tnum))
        self.points_per_trace = np.zeros((1, tnum))
        self.topography = np.zeros((1, tnum))
        self.bytes_per_point = np.zeros((1, tnum))
        self.n_stackes = np.zeros((1, tnum))
        self.time_window = np.zeros((1, tnum))
        self.pos = np.zeros((3, tnum))
        self.receive = np.zeros((3, tnum))
        self.transmit = np.zeros((3, tnum))
        self.tz_adjustment = np.zeros((1, tnum))
        self.zero_flag = np.zeros((1, tnum))
        self.time_of_day = np.zeros((1, tnum))
        self.comment_flag = np.zeros((1, tnum))
        self.comment = ['' for i in range(tnum)]

    def get_header(self, offset, f_lines):
        """Get the header information for a single trace."""
        header = struct.unpack('<25f', f_lines[offset: offset + 25 * 4])
        comment = struct.unpack('<28c',
                                f_lines[offset + 25 * 4: offset + 25 * 4 + 28])
        self.trace_numbers[0, self.header_index] = header[0]
        self.positions[0, self.header_index] = header[1]
        self.points_per_trace[0, self.header_index] = header[2]
        self.topography[0, self.header_index] = header[3]
        self.bytes_per_point[0, self.header_index] = header[5]
        self.n_stackes[0, self.header_index] = header[7]
        self.time_window[0, self.header_index] = header[8]
        self.pos[0, self.header_index] = header[9]
        self.pos[1, self.header_index] = header[11]
        self.pos[2, self.header_index] = header[13]
        self.receive[0, self.header_index] = header[14]
        self.receive[1, self.header_index] = header[15]
        self.receive[2, self.header_index] = header[16]
        self.transmit[0, self.header_index] = header[17]
        self.transmit[1, self.header_index] = header[18]
        self.transmit[2, self.header_index] = header[19]
        self.tz_adjustment[0, self.header_index] = header[20]
        self.zero_flag[0, self.header_index] = header[21]
        self.time_of_day[0, self.header_index] = header[23]
        self.comment_flag[0, self.header_index] = header[24]
        self.comment[self.header_index] = str(comment[0])
        self.header_index += 1


def partition_project_file(fn_project):
    """Separate profiles.
    The new pulse ekko dvl writes 'project' files with all the profiles stored
    together. We want to break them out into all the .HD header files and .DT1
    data files.
    Parameters
    ----------
    fn_project: str
        Filename for the .gpz project file
    """
    with open(fn_project, 'rb') as fin:
        f = fin.read()

    profile_num = 1
    while f.find(b'line%d' % profile_num) != -1:
        # Get the header file
        hd_start = f.find(b'line%d.hd' % (profile_num))
        hd_end = f[hd_start:].find(b'PK') + hd_start
        hd_str = str(f[hd_start:hd_end])
        hd_lines = hd_str.split('\\r\\n')
        hd_lines[0] = hd_lines[0][2:]
        hd_lines[-1] = ''

        # Get the 'ini' file
        ini_start = f.find(b'line%d.ini' % (profile_num))
        ini_end = f[ini_start:].find(b'PK') + ini_start
        ini_str = str(f[ini_start:ini_end])
        for i, line in enumerate(ini_str.split('\\r\\n')):
            if i == 0:
                hd_lines.append(line[2:len('line%d.ini' % (profile_num)) + 2])
                hd_lines.append(line[len('line%d.ini' % (profile_num)) + 2:])
            elif i == len(ini_str.split('\\r\\n')) - 1:
                continue
            else:
                hd_lines.append(line)

        # Write to the header file
        with open('LINE' + str(profile_num) + '.HD', 'w') as fout:
            for line in hd_lines:
                fout.write(line + '\n')

        # Get the data file
        dt_start = f.find(b'line%d.dt1' % (profile_num))
        dt_start += len(b'line%d.dt1' % (profile_num))
        dt_end = f[dt_start:].find(b'Lineset') + dt_start
        dt_str = f[dt_start:dt_end]
        # Write to the data file
        with open('LINE' + str(profile_num) + '.DT1', 'wb') as fout:
            fout.write(dt_str)

        profile_num += 1


# method to read pulseekko data
def read(fpath, navcrs, body):
    """Load data from a pulse_ekko file."""
    rdata = radar(fpath)
    rdata.fn = fpath.split("/")[-1][:-4]
    print("----------------------------------------")
    print("Loading: " + rdata.fn)
    infile_gps = fpath[:-4] + ".GPS"
    infile_hd = fpath[:-4] + ".HD"

    try:
        strtypes = (unicode, str)
        openmode_unicode = 'rU'
    except NameError:
        strtypes = (str, )
        openmode_unicode = 'r'

    with open(infile_hd, openmode_unicode) as fin:
        if fin.read().find('1.5.340') != -1:
            pe_version = '1.5.340'
        else:
            pe_version = '1.0'
        fin.seek(0)
        for i, line in enumerate(fin):
            if 'TRACES' in line or 'NUMBER OF TRACES' in line:
                rdata.tnum = int(line.rstrip('\n\r ').split(' ')[-1])
            if 'PTS' in line or 'NUMBER OF PTS/TRC' in line:
                rdata.snum = int(line.rstrip('\n\r ').split(' ')[-1])
            if ('WINDOW' in line and 'AMPLITUDE' not in line) or 'TOTAL TIME WINDOW' in line:
                window = float(line.rstrip('\n\r ').split(' ')[-1])
            if 'TIMEZERO' in line or 'TIMEZERO AT POINT' in line:
                trig = int(float(line.rstrip('\n\r ').split(' ')[-1])
                                   ) * np.ones((rdata.tnum,))
            if i == 4 and pe_version == '1.0':
                try:
                    doy = (int(line[6:10]), int(line[1:2]), int(line[3:5]))
                except ValueError:
                    doy = (int(line[:4]), int(line[5:7]), int(line[8:10]))
            if i == 2 and pe_version == '1.5.340':
                doy = (int(line[6:10]), int(line[:2]), int(line[3:5]))

    if pe_version == '1.0':
        rdata.dat = np.zeros((rdata.snum, rdata.tnum), dtype=np.int16)
    elif pe_version == '1.5.340':
        rdata.dat = np.zeros((rdata.snum, rdata.tnum), dtype=np.float32)

    rdata.traceheaders = TraceHeaders(rdata.tnum)
    with open(fpath, 'rb') as fin:
        lines = fin.read()

    offset = 0
    for i in range(rdata.tnum):
        rdata.traceheaders.get_header(offset, lines)
        offset += 25 * 4 + 28
        if pe_version == '1.0':
            trace = struct.unpack('<{:d}h'.format(rdata.snum),
                                  lines[offset: offset + rdata.snum * 2])
            offset += rdata.snum * 2
        elif pe_version == '1.5.340':
            fmt = '<%df' % (len(lines[offset: offset + rdata.snum * 4]) // 4)
            trace = struct.unpack(fmt, lines[offset:offset + rdata.snum * 4])
            offset += rdata.snum * 4

        # trace -= np.nanmean(trace[:100])
        # rdata.dat[:, i] = trace.copy()
        rdata.dat[:,i] = trace


    # known vars that are not really set
    rdata.nchan = 1
    rdata.trace_num = np.arange(rdata.tnum) + 1

    # Power some more real variables
    rdata.dt = window / rdata.snum * 1.0e-9

    # convert signed int amplitude to floating point for displaying
    rdata.set_proc(rdata.dat.astype(np.float))

    rdata.set_sim(np.ones(rdata.dat.shape))                # place holder for clutter data

    # assign signal info
    rdata.sig["signal type"] = "impulse"

    # create nav object to hold lon, lat, elev
    rdata.navdf = navparse.getnav_pulseekko(infile_gps, rdata.tnum, navcrs, body)

    # for ground-based GPR, elev_gnd is the same as GPS recorded elev
    rdata.set_srfElev(rdata.navdf["elev"])

    return rdata