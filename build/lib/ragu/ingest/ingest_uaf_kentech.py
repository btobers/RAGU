# RAGU - Radar Analysis Graphical Utility
#
# copyright © 2020 btobers <tobers.brandon@gmail.com>
#
# distributed under terms of the GNU GPL3.0 license
"""
ingest_uaf_kentech is a module developed to ingest Martin Truffer's Kentech radar sounding data. 
"""
### imports ###
from ragu.radar import garlic
from ragu.nav import navparse
from ragu.tools import utils
import h5py, fnmatch
import numpy as np
import scipy as sp
import sys

# method to ingest OIB-AK radar hdf5 data format
def read_h5(fpath, navcrs, body):
    rdata = garlic(fpath)
    rdata.fn = fpath.split("/")[-1][:-3]
    rdata.dtype = "uaf_kentech"

    # read in .h5 file
    f = h5py.File(rdata.fpath, "r")                      

    # h5 radar data group structure        
    # |-raw
    # |  |-rx0
    # |  |-tx0    
    # |  |-loc0
    # |-ext
    # |  |-nav0
    # |  |-srf0
    # |-drv
    # |  |-proc0
    # |  |-clutter0
    # |  |-pick

    # pull necessary raw group data
    rdata.snum = int(f["raw"]["rx0"].attrs["samplesPerTrace"])                  # samples per trace in rgram
    rdata.tnum = int(f["raw"]["rx0"].attrs["numTrace"])                         # number of traces in rgram 
    rdata.fs = f["raw"]["rx0"].attrs["samplingFrequency"]                       # sampling frequency
    rdata.dt = 1/rdata.fs                                                       # sampling interval, sec
    rdata.prf = 1000                                                            # pulse repition frequency, Hz
    rdata.nchan = 1

    # pull radar proc and sim arrayss
    rdata.set_dat(f["drv/proc0"][:])                                            # pulse compressed array
    rdata.set_proc(np.abs(rdata.get_dat()))

    rdata.set_twtt()
    # assign signal info
    # rdata.info["Signal Type"] = f["raw"]["tx0"].attrs["signal"].capitalize() 
    # rdata.info["CF [MHz]"] = f["raw"]["tx0"].attrs["centerFrequency"][0] * 1e-6
    # if rdata.info["Signal Type"] == "Chirp":
    #     rdata.info["Badwidth [%]"] = f["raw"]["tx0"].attrs["bandwidth"][0] * 100
    #     rdata.info["Pulse Length [\u03BCs]"] = f["raw"]["tx0"].attrs["length"][0] * 1e6
    # rdata.info["Sampling Frequency [MHz]"] = rdata.fs * 1e-6
    # rdata.info["PRF [kHz]"] = rdata.prf * 1e-3

    # parse nav
    rdata.navdf = navparse.getnav_uaf_kentech(fpath, navcrs, body)

    f.close()                                                   # close the file

    rdata.check_attrs()

    return rdata