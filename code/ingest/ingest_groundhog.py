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

    # groundhog h5 radar data group structure        
    # |-raw
    # |  |-rx0
    # |  |-gps0
    # |  |-rxFix0    
    # |  |-txFix0

    # pull necessary raw group data
    rdata.fs = f["raw/rx0"].attrs["fs"]                                         # sampling frequency
    rdata.dt = 1/rdata.fs                                                       # sampling interval, sec
    rdata.prf = 1e3/f["raw"]["rx0"].attrs["stack"]                              # pulse repition frequency, Hz
    rdata.nchan = 1

    # pull radar proc and sim arrayss
    rdata.set_dat(f["restack/rx0"][:])                                            # pulse compressed array
    rdata.set_proc(np.abs(rdata.get_dat()))
    rdata.snum, rdata.tnum = rdata.get_dat().shape

    rdata.set_twtt()

    # parse nav
    rdata.navdf = navparse.getnav_groundhog(fpath, navcrs, body)

    # if rx and tx each have gps, we'll store antenna sep per trace
    if "asep" in rdata.navdf:
        rdata.asep = rdata.navdf["asep"].to_numpy()
    else:
        rdata.asep = 100

    # groudnhog rx triggers on arrival of airwave and records 32 samples at top of each trace before trigger - so sample zero is sample 33
    rdata.flags.sampzero = 33
    rdata.tzero_shift()

    # define surface horizon name to set index to zeros
    rdata.pick.horizons["srf"] = np.zeros(rdata.tnum)
    rdata.pick.set_srf("srf")

    # for ground-based GPR, srf_elev is the same as GPS recorded elev
    rdata.set_srfElev(dat = rdata.navdf["elev"].to_numpy())

    rdata.info["Signal Type"] = "Impulse" 
    rdata.info["Sampling Frequency [MHz]"] = rdata.fs * 1e-6
    rdata.info["PRF [kHz]"] = rdata.prf * 1e-3
    rdata.info["Stack"] = f["raw"]["rx0"].attrs["stack"]
    rdata.info["Antenna Separation [m]"] = round(np.nanmean(rdata.asep),2)

    f.close()                                                   # close the file

    rdata.check_attrs()

    try:
        rdata.filter(btype='lowpass', lowcut=None, highcut=4e6, order=5, direction=0)
    except:
        pass
    try:
        rdata.filter(btype='lowpass', lowcut=None, highcut=.4, order=5, direction=1)
    except:
        pass

    return rdata