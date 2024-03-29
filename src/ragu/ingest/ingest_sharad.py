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
from ragu.radar import garlic
from ragu.nav import navparse
from ragu.tools import utils
import numpy as np
import os, sys

# method to read PDS SHARAD USRDR data
def read(fpath, simpath, navcrs, body):
    rdata = garlic(fpath)
    if fpath.endswith("sim.img") or fpath.endswith("geom_combined.img"):
        return rdata
    rdata.fn = fpath.split("/")[-1][:-10]
    rdata.dtype = "sharad"
    root = os.path.dirname(fpath)

    # rdata.fn = fn.rstrip("_rgram.img")
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
    # account for PDS v4 sim format and legacy geom_combined format
    if simpath:
        simpath = simpath + "/" + rdata.fn + "_sim.img"
        if not os.path.isfile(simpath):
            simpath = simpath + "/" + rdata.fn + "_geom_combined.img"

    else:
        simpath = root + "/" + rdata.fn + "_sim.img"
        if not os.path.isfile(simpath):
            simpath = root + "/" + rdata.fn + "_geom_combined.img"

    if os.path.isfile(simpath):
        with open(simpath, "rb") as f:
            sim = np.fromfile(f, dtype)
        # reshape - will be different depending on sim version
        if simpath.endswith('sim.img'):
            # just take combined sim if PDS v4 sim
            sim = sim[2 * len(sim) // 3 :].reshape(rdata.snum,rdata.tnum)
        else:
            sim = sim.reshape(rdata.snum, rdata.tnum)
    
        rdata.set_sim(sim)
    else:
        print("Clutter simulation not found in:\t{}\nSpecify alternate path in configuration file.".format(simpath.rstrip(simpath.split('/')[-1])))

    rdata.set_twtt()

    # assign signal info
    rdata.info["signal type"] = "chirp"
    rdata.info["cf [MHz]"] = 20
    rdata.info["badwidth [%]"] = 50
    rdata.info["pulse length [\u03BCs]"] = 85
    rdata.info["prf [Hz]"] = rdata.prf

    # open geom nav file for rgram
    geom_path = root +  "/" + rdata.fn + "_geom.tab"

    # parse nav
    rdata.geocrs = navcrs
    rdata.xyzcrs = navparse.xyzsys[body]
    rdata.navdf = navparse.getnav_sharad(geom_path, navcrs, body)

    rdata.set_srfElev(dat = np.repeat(np.nan, rdata.tnum))

    rdata.check_attrs()

    return rdata