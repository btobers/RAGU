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
from ragu.radar import garlic
from ragu.nav import navparse
from ragu.tools import utils
import h5py, fnmatch
import numpy as np
import scipy as sp
import sys

# method to ingest groundhog hdf5 data format
def read_h5(fpath, navcrs, body):
    rdata = garlic(fpath)
    rdata.fn = fpath.split("/")[-1][:-3]
    rdata.dtype = "groundhog"

    # read in .h5 file
    f = h5py.File(rdata.fpath, "r")                      

    # pull necessary raw group data
    rdata.fs = f["raw/rx0"].attrs["fs"]                             # sampling frequency
    rdata.dt = 1/rdata.fs
    try:                                                            # sampling interval, sec
        rdata.prf = f["raw/rx0"].attrs["prf"]                       # pulse repition frequency, Hz
    except KeyError:
        rdata.prf = 0
    rdata.nchan = 1

    # pull radar proc and sim arrayss
    if("restack" in f.keys()):
        rdata.set_dat(f["restack/rx0"][:].astype(float))
    else:
        rdata.set_dat(f["raw/rx0"][:].astype(float))

    # want to plot positive and negative amplitude values - don't dB 
    rdata.dbit = False
    rdata.set_proc(rdata.get_dat())
    rdata.snum, rdata.tnum = rdata.get_dat().shape

    rdata.set_twtt()

    # parse nav
    rdata.geocrs = navcrs
    rdata.xyzcrs = navparse.xyzsys[body]
    rdata.navdf = navparse.getnav_groundhog(fpath, navcrs, body)

    # if rx and tx each have gps, we'll store antenna sep per trace
    if "asep" in rdata.navdf:
        rdata.asep = rdata.navdf["asep"].to_numpy()
    else:
        rdata.asep = 50

    # groudnhog rx triggers on arrival of airwave - get number of traces pre-trigger to vertically shift the data accordingly
    try:
        pt = f["raw/rx0"].attrs["pre_trig"]
    except KeyError:
        pt = f["raw/rx0"].attrs["pre_trigger"]

    rdata.flags.sampzero = pt+1
    rdata.tzero_shift()

    # define surface horizon name to set index to zeros
    rdata.pick.horizons["srf"] = np.zeros(rdata.tnum)
    rdata.pick.set_srf("srf")

    # srf_elev is the same as GPS recorded elev
    rdata.set_srfElev(dat = rdata.navdf["elev"].to_numpy())

    rdata.info["Signal Type"] = "Impulse" 
    rdata.info["Sampling Frequency [MHz]"] = rdata.fs * 1e-6
    rdata.info["PRF [kHz]"] = rdata.prf * 1e-3
    rdata.info["Stack"] = f["raw/rx0"].attrs["stack"]
    rdata.info["Antenna Separation [m]"] = round(np.nanmean(rdata.asep))

    f.close()                                                   # close the file

    rdata.check_attrs()

    # try:
    #     rdata.filter(btype='lowpass', lowcut=None, highcut=3e6, order=5, direction=0)
    # except:
    #     pass
    # try:
    #     rdata.filter(btype='lowpass', lowcut=None, highcut=.4, order=5, direction=1)
    # except:
    #     pass

    return rdata