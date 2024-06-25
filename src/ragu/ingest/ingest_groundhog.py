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

    # get system info
    try:
        if "Blue Systems" in f.attrs["system"]:
            rdata.dtype = "bsi"
            rdata.dbit = True
    except KeyError:
        rdata.dtype = "ghog"
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

    # groudnhog rx triggers on arrival of airwave - get number of traces pre-trigger to vertically shift the data accordingly
    try:
        pt = f["raw/rx0"].attrs["pre_trig"]
    except KeyError:
        pt = f["raw/rx0"].attrs["pre_trigger"]

    rdata.flags.sampzero = pt+1
    rdata.tzero_shift()

    # pull some info
    rdata.info["Signal Type"] = "Impulse" 
    rdata.info["Sampling Frequency [MHz]"] = rdata.fs * 1e-6
    rdata.info["PRF [kHz]"] = rdata.prf * 1e-3
    rdata.info["Stack"] = f["raw/rx0"].attrs["stack"]
    rdata.info["Antenna Separation [m]"] = round(np.nanmean(rdata.asep))

    rdata.check_attrs()                                         # check basic rdata attributes
    f.close()                                                   # close file


    # initialize surface arrays - if groundhog, surface is at zero after shifting by pretrigger amount. If BSI airIPR initialize nan array for surface pick horizon and elevation array
    if rdata.dtype == "ghog":
        # define surface horizon name to set index to zeros
        arr = np.zeros(rdata.tnum)
        # srf_elev is the same as GPS recorded elev
        rdata.set_srfElev(dat = rdata.navdf["elev"].to_numpy())
    elif rdata.dtype == "bsi":
        arr = np.repeat(np.nan, rdata.tnum)
        rdata.set_srfElev(dat = arr)
        try:
            rdata.filter(btype='bandpass', lowcut=2.5e6, highcut=20e6, order=5, direction=0)
        except:
            pass
        try:
            rdata.removeSlidingMeanFFT(window=250)
        except:
            pass

    rdata.pick.horizons["srf"] = arr
    rdata.pick.set_srf("srf")

    return rdata