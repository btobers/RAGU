# RAGU - Radar Analysis Graphical Utility
#
# copyright © 2020 btobers <tobers.brandon@gmail.com>
#
# distributed under terms of the GNU GPL3.0 license
"""
ingest_marsis_ipc is a module developed to ingest MARSIS radar sounding data processed by Michael Christoffersen. 
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
    rdata = garlic(fpath)
    rdata.fn = fpath.split("/")[-1][:-4]
    rdata.dtype = "marsis_ipc"
    root = os.path.dirname(fpath)

    # convert binary RGRAM to numpy array
    # # reshape array, knowing that each trace has 512 samples
    dtype = np.dtype("float32")     
    with open(fpath, "rb") as f:
        tmp = np.fromfile(f, dtype)     
    l = len(tmp)

    rdata.snum = 512
    rdata.tnum = int(len(tmp)/rdata.snum)
    rdata.fs = 1.4e6
    rdata.dt = rdata.fs
    rdata.prf = 127
    rdata.nchan = 1
    rdata.set_dat(tmp.reshape((rdata.snum,rdata.tnum), order='F'))
    rdata.set_proc(rdata.get_dat())

    # convert binary .img clutter sim product to numpy array
    if simpath:
        simpath = simpath + "/" + rdata.fn + "_geom_combined.img"
    else:
        simpath = root + "/" + rdata.fn + "_geom_combined.img"

    if os.path.isfile(simpath):
        with open(simpath, "rb") as f:
            sim = np.fromfile(f, dtype)   
        sim = sim.reshape(rdata.snum,rdata.tnum)
        rdata.set_sim(sim)
    else:
        print("Clutter simulation not found:\t{}\nSpecify alternate path in configuration file.".format(simpath))

    rdata.set_twtt()

    # assign signal info
    rdata.info["dataset"] = "marsis_ipc"
    # rdata.info["signal type"] = "chirp"
    # rdata.info["cf [MHz]"] = 20
    # rdata.info["badwidth [%]"] = 50
    # rdata.info["pulse length [\u03BCs]"] = 85
    rdata.info["sampling frequency [MHz]"] = rdata.fs * 1e-6
    rdata.info["prf [Hz]"] = rdata.prf

    # open geom nav file for rgram
    geom_path = root +  "/" + rdata.fn[:-2] + "nav.csv"

    # parse nav
    rdata.geocrs = navcrs
    rdata.xyzcrs = navparse.xyzsys[body]
    rdata.navdf = navparse.getnav_marsis_ipc(geom_path, navcrs, body)

    rdata.set_srfElev(dat = np.repeat(np.nan, rdata.tnum))

    rdata.check_attrs()

    return rdata