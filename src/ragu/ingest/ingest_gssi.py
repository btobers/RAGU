# RAGU - Radar Analysis Graphical Utility
#
# copyright © 2020 btobers <tobers.brandon@gmail.com>
#
# distributed under terms of the GNU GPL3.0 license
"""
this module contains functions parsed from https://github.com/iannesbitt/readgssi to read gssi dzt files and associated dzg files for use in RAGU
much of the header data which is not necessary for RAGU use has been removed
"""
### imports ###
from ragu.radar import garlic
from ragu.nav import navparse
from ragu.tools.constants import *
import struct
import os,sys
import numpy as np

# method to read gssi dzt data
def read(fpath, navcrs, body):
    fn = fpath.split("/")[-1]
    rdata = garlic(fpath)
    rdata.fn = fn[:-4]
    rdata.dtype = "gssi"

    # modified readgssi readdzt.dzt reader (credit, DOI: 10.5281/zenodo.3352438)
    with open(rdata.fpath, "rb") as f:

        # skip around and read necessary attributes
        f.seek(2)
        data_offset = struct.unpack("<h", f.read(2))[0]     # offset to data array [bits]
        rdata.snum = struct.unpack('<h', f.read(2))[0]      # number of samples per trace
        bits = struct.unpack('<h', f.read(2))[0]            # number of bits - datatype
        f.seek(10)
        rdata.prf = struct.unpack('<f', f.read(4))[0]       # scans per second (prf)
        f.seek(26)
        range_ns = struct.unpack('<f', f.read(4))[0]        # data range [ns] - record time per trace
        f.seek(52)
        rdata.nchan = struct.unpack('<h', f.read(2))[0]     # number of data channels
        rdata.dt = range_ns / rdata.snum * 1.0e-9           # sampling interval
        rdata.fs = 1/rdata.dt                               # sampling freq

        if bits == 8:
            dtype = np.uint8    # 8-bit unsigned
        elif bits == 16:
            dtype = np.uint16   # 16-bit unsigned
        elif bits == 32:
            dtype = np.int32    # 32-bit signed
        else:
            print("ingest_gssi.read error: undefined data type. #bits = " + bits)
            exit(1)

        # skip ahead to data
        if data_offset < 1024: # whether or not the header is normal or big-->determines offset to data array
            didx = 1024 * data_offset
        else:
            didx = 1024 * rdata.chan

        # skip to data index
        f.seek(didx)

        # read in data - need to transpose to get correct shape
        rdata.set_dat(np.fromfile(f, dtype).reshape(-1,(rdata.snum*rdata.nchan)).T)

    # ensure data file is not empty
    if not np.any(rdata.dat):
        raise ValueError("gssi_read error: file contains no radar data")

    rdata.tnum = rdata.dat.shape[1]

    # convert gssi signed int amplitude to floating point for displaying
    rdata.set_proc(rdata.get_dat().astype(np.float))

    rdata.set_twtt()

    # assign signal info
    rdata.info["Signal Type"] = "Impulse"
    rdata.info["Sampling Frequency [MHz]"] = rdata.fs * 1e-6
    rdata.info["PRF [kHz]"] = rdata.prf * 1e-3

    # read in gps data if exists
    infile_gps = fpath.replace(".DZT",".DZG")

    # create nav object to hold lon, lat, hgt
    rdata.geocrs = navcrs
    rdata.xyzcrs = navparse.xyzsys[body]
    rdata.navdf = navparse.getnav_gssi(infile_gps, rdata.tnum, navcrs, body)

    # for ground-based GPR, elev_gnd is the same as GPS recorded elev
    rdata.set_srfElev(dat = rdata.navdf["elev"].to_numpy())

    rdata.check_attrs()

    return rdata