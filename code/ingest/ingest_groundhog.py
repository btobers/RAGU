# RAGU - Radar Analysis Graphical Utility
#
# copyright © 2020 btobers <tobers.brandon@gmail.com>
#
# distributed under terms of the GNU GPL3.0 license
"""
ingest_oibAK is a module developed to ingest NASA OIB-AK radar sounding data. 
primary data format is hdf5, however some older data is still being converted over from .mat format
"""
### imports ###
from radar import garlic
from nav import navparse
from tools import utils
import h5py, fnmatch
import numpy as np
import scipy as sp
import sys

# method to ingest OIB-AK radar hdf5 data format
def read_h5(fpath, navcrs, body):
    rdata = garlic(fpath)
    rdata.fn = fpath.split("/")[-1][:-3]
    rdata.dtype = "groundhog"

    # read in .h5 file
    print("----------------------------------------")
    print("Loading: " + rdata.fn)
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
    rdata.fs = f["raw/rx0"].attrs["fs"]                                      # sampling frequency
    rdata.dt = 1/rdata.fs                                                       # sampling interval, sec
    # rdata.prf = f["raw"]["tx0"].attrs["pulseRepetitionFrequency"][0]            # pulse repition frequency, Hz
    rdata.nchan = 1

    # pull radar proc and sim arrayss
    rdata.set_dat(f["raw/rx0"][:])                                            # pulse compressed array
    rdata.set_proc(np.abs(rdata.get_dat()))
    rdata.snum, rdata.tnum = rdata.get_dat().shape

    rdata.set_twtt()

    # parse nav
    rdata.navdf = navparse.getnav_groundhog(fpath, navcrs, body)

    f.close()                                                   # close the file

    rdata.check_attrs()

    return rdata