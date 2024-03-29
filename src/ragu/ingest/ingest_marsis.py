# RAGU - Radar Analysis Graphical Utility
#
# copyright © 2020 btobers <tobers.brandon@gmail.com>
#
# distributed under terms of the GNU GPL3.0 license
"""
ingest_marsis is a module developed to ingest JPL MARSIS radar sounding data. 
data format is binary 32-bit floating point pulse compressed data
"""
### imports ###
from ragu.radar import garlic
from ragu.nav import navparse
from ragu.tools import utils
from PIL import Image
import numpy as np
import os, sys, glob
import matplotlib.pyplot as plt

# method to read JPL multilook MARSIS data
def read(fpath, simpath, navcrs, body):
    fn = fpath.split("/")[-1]
    root = fpath.rstrip(fn)
    orbit = fn.split('_')
    orbit = orbit[0] + '_' + orbit[1]
    rdata = garlic(fpath)
    rdata.fn = fn[:-4]
    rdata.dtype = "marsis"

    # convert binary RGRAM to numpy array
    # # reshape array
    dtype = np.dtype("float32")     
    with open(fpath, "rb") as f:
        dat = np.fromfile(f, dtype)     
    l = len(dat)

    rdata.snum = 2048
    # get number of traces, dividing file length by number of samples per trace, by 8 data arrays
    rdata.tnum = int(l/rdata.snum/8)
    # dt per pixel from reprocessed oversampled data - data is oversampled by factor of 2
    rdata.fs = 2*(1.4e6)
    rdata.dt = 1/rdata.fs
    rdata.prf = 127
    rdata.nchan = 2

    # reshape into 8 stacked rgrams
    dat = dat.reshape((rdata.snum*8,rdata.tnum),order="F")

    # reprocessed MARSIS data should be bottom two rgrams
    dat = dat[-(rdata.snum*rdata.nchan):,:]

    # reshape into stacked 3D array for two channels
    tmp = np.zeros((rdata.snum,rdata.tnum,rdata.nchan))
    tmp[:,:,0] = dat[:rdata.snum,:]
    tmp[:,:,1] = dat[-rdata.snum:,:]
    # apparently data arrays are already power values, so revert to amplitude (abs(amplitude))
    rdata.set_dat(np.sqrt(tmp))
    rdata.set_proc(rdata.get_dat())

    # convert png clutter sim product to numpy array
    if simpath:
        simpath = simpath + "/" + orbit + "_clutter.img"
    else:
        simpath = root + "/" + orbit + "_clutter.img"

    if os.path.isfile(simpath):
        with open(simpath,"rb") as f:
            dat = np.fromfile(f, np.uint8)
            sim = dat.reshape(rdata.snum, rdata.tnum)
            rdata.set_sim(sim)
    else:
        print("Clutter simulation not found:\t{}\nSpecify alternate path in configuration file.".format(simpath))

    rdata.set_twtt()

    # assign signal info
    rdata.info["Signal Type"] = "Chirp"
    rdata.info["Sampling Frequency [MHz]"] = rdata.fs*1e-6
    rdata.info["PRF [Hz]"] = rdata.prf

    # open geom nav file for rgram
    geom_path = root + orbit + "_geom.tab"
 
    # parse nav
    rdata.geocrs = navcrs
    rdata.xyzcrs = navparse.xyzsys[body]
    rdata.navdf = navparse.getnav_marsis(geom_path, navcrs, body)

    rdata.set_srfElev(dat = np.repeat(np.nan, rdata.tnum))

    rdata.check_attrs()

    return rdata