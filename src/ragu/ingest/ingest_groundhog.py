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

    # get appropriate data grou
    grps = f.keys()
    if "proc" in grps:
        grp = "proc"
    elif "restack" in grps:
        grp = "restack"
    else: 
        grp = "raw"


    # pull necessary raw group data
    rdata.fs = f[grp]["rx0"].attrs["fs"]                             # sampling frequency
    rdata.dt = 1/rdata.fs
    try:                                                            # sampling interval, sec
        rdata.prf = f[grp]["rx0"].attrs["prf"]                       # pulse repition frequency, Hz
    except KeyError:
        rdata.prf = 0

    rdata.nchan = 1


    rdata.set_dat(f[grp]["rx0"][:].astype(float))

    # get system info
    try:
        if "Blue Systems" in f[grp]["rx0"].attrs["system"]:
            rdata.dtype = "bsi"
            try:
                rdata.set_sim(f["drv"]["clutter0"][:])              # simulated clutter array
            except KeyError:
                pass
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
        pt = f[grp]["rx0"].attrs["pre_trig"]
    except KeyError:
        pt = f[grp]["rx0"].attrs["pre_trigger"]

    rdata.flags.sampzero = pt
    if pt>0:
        rdata.tzero_shift()

    # pull some info
    rdata.info["Signal Type"] = "Impulse" 
    rdata.info["Sampling Frequency [MHz]"] = rdata.fs * 1e-6
    rdata.info["PRF [kHz]"] = rdata.prf * 1e-3
    rdata.info["Stack"] = f[grp]["rx0"].attrs["stack"]
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

        # optional processing defaults
        # rdata.filter(btype='bandpass', lowcut=2.5e6, highcut=20e6, order=5, direction=0)
        # rdata.removeSlidingMeanFFT(window=250)
        rdata.tpowGain(1.5)

    # init surface and bed horizons
    rdata.pick.horizons["srf"] = arr
    rdata.pick.set_srf("srf")
    arr = np.repeat(np.nan, rdata.tnum)
    rdata.pick.horizons["bed"] = arr

    return rdata