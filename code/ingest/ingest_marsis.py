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
from radar import garlic
from nav import navparse
from tools import utils
from PIL import Image
import numpy as np
import os, sys, glob
import matplotlib.pyplot as plt

# method to read JPL multilook MARSIS data
def read(fpath, simpath, navcrs, body):
    orbit = fpath.split("/")[-2]
    fn = fpath.split("/")[-1]
    root = fpath.rstrip(fn)
    rdata = garlic(fpath)
    rdata.fn = orbit + "_" + fn.replace(".","_")[:-4]
    rdata.dtype = "marsis"
    print("----------------------------------------")
    print("Loading: " + rdata.fn)

    # convert binary RGRAM to numpy array
    # # reshape array
    dtype = np.dtype("float32")     
    with open(fpath, "rb") as f:
        dat = np.fromfile(f, dtype)     
    l = len(dat)

    rdata.snum = 2048
    # get number of traces, dividing file length by number of samples per trace, by 8 data arrays
    rdata.tnum = int(l/rdata.snum/8)
    # dt per pixel from reprocessed oversampled data
    rdata.dt = 1/(2*(1.4e6))
    rdata.prf = 127
    rdata.nchan = 2

    # reshape into 8 stacked rgrams
    dat = dat.reshape((rdata.snum*8,rdata.tnum),order="F")

    # reprocessed MARSIS data should be bottom two rgrams
    dat = dat[-(rdata.snum*rdata.nchan):,:]

    # reshape into stacked 3D array for two channels
    rdata.dat = np.zeros((rdata.snum,rdata.tnum,rdata.nchan))
    rdata.dat[:,:,0] = dat[:rdata.snum,:]
    rdata.dat[:,:,1] = dat[-rdata.snum:,:]
    # apparently data arrays are already power values, so revert to amplitude (abs(amplitude))
    rdata.dat = np.sqrt(rdata.dat)
    rdata.set_proc(rdata.dat)

    # convert png clutter sim product to numpy array
    if simpath:
        simpath = simpath + "/" + orbit + "_clutterSim_multilook_analysis.png"
    else:
        simpath = root + "/" + orbit + "_clutterSim_multilook_analysis.png"

    if os.path.isfile(simpath):
        image = Image.open(simpath)
        # convert image to numpy array
        sim = np.asarray(image)
        sim = sim[int(rdata.snum/2):-int(rdata.snum/2),:]
    else:
        sim = np.ones((rdata.snum,rdata.tnum))

    rdata.set_sim(sim)

    # assign signal info
    rdata.info["signal type"] = "chirp"

    # open geom nav file for rgram
    geom_path = glob.glob(root + "*tab")[0]
 
    # parse nav
    rdata.navdf = navparse.getnav_marsis(geom_path, navcrs, body)

    rdata.set_srfElev(dat = np.repeat(np.nan, rdata.tnum))

    return rdata