# RAGU - Radar Analysis Graphical Utility
#
# copyright © 2020 btobers <tobers.brandon@gmail.com>
#
# distributed under terms of the GNU GPL3.0 license
"""
ingest_sharad is a module developed to ingest NASA MRO-SHARAD FPB radar sounding data. 
data format is binary 32-bit floating point pulse compressed amplitude data acquired from the PDS
"""
### imports ###
from radar import garlic
from nav import navparse
from tools import utils
import numpy as np
import os, sys

# method to read PDS SHARAD USRDR data
def read(fpath, simpath, navcrs, body):
    fn = fpath.split("/")[-1]
    root = fpath.rstrip(fn)
    print("----------------------------------------")
    print("Loading: " + fn)
    rdata = garlic(fpath)
    rdata.fn = fn.rstrip("_rgram.img")
    rdata.dtype = "sharad"
    # convert binary .img PDS RGRAM to numpy array
    # reshape array with 3600 lines
    dtype = np.dtype("float32")     
    with open(fpath, "rb") as f:
        tmp = np.fromfile(f, dtype)     
    l = len(tmp)

    rdata.snum = 3600
    rdata.tnum = int(len(tmp)/rdata.snum)
    rdata.dt = .0375e-6
    rdata.prf = 700.28
    rdata.nchan = 1
    rdata.set_dat(tmp.reshape(rdata.snum,rdata.tnum))
    rdata.set_proc(rdata.get_dat())
    
    # convert binary .img clutter sim product to numpy array
    if simpath:
        simpath = simpath + fn.replace("rgram","geom_combined")
    else:
        simpath = root + fn.replace("rgram","geom_combined")

    if os.path.isfile(simpath):
        with open(simpath, "rb") as f:
            sim = np.fromfile(f, dtype)   
        sim = sim.reshape(rdata.snum,rdata.tnum)
        rdata.set_sim(sim)
    else:
        print("Clutter simulation not found:\t{}\nSpecify alternate path in configuration file.".format(simpath))

    rdata.set_twtt()

    # assign signal info
    rdata.info["signal type"] = "chirp"
    rdata.info["cf [MHz]"] = 20
    rdata.info["badwidth [%]"] = 50
    rdata.info["pulse length [\u03BCs]"] = 85
    rdata.info["prf [Hz]"] = rdata.prf

    # open geom nav file for rgram
    geom_path = root + fn.replace("rgram","geom").replace("img","tab")

    # parse nav
    rdata.navdf = navparse.getnav_sharad(geom_path, navcrs, body)

    rdata.set_srfElev(dat = np.repeat(np.nan, rdata.tnum))

    rdata.check_attrs()

    return rdata