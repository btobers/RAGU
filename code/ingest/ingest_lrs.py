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
from radar import radar
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

    # Get # of traces
    fd = open(fpath,'r')
    lbl = fd.read().split('\n')
    fd.close()

    rdata = radar(fpath.replace(".lbl", ".img"))
    rdata.tnum = int(lbl[19].split('=')[1])
    rdata.snum = 1000

    rdata.fn = fn.rstrip(".lbl")
    rdata.dtype = "lrs"
    # convert binary .img PDS RGRAM to numpy array
    # reshape array with 3600 lines
    with open(rdata.fpath, "rb") as f:
        f.seek(rdata.tnum*55)
        data = f.read(rdata.tnum*rdata.snum)
        rdata.dat = np.frombuffer(data, np.uint8)     
    l = len(rdata.dat)

    rdata.dt = 305.17578125e-09
    rdata.nchan = 1
    rdata.dat = rdata.dat.reshape(rdata.snum,rdata.tnum)
    rdata.set_proc(rdata.dat)
    
    # convert binary .img clutter sim product to numpy array
    if simpath:
        simpath = simpath + "/" + fn.replace(".lbl","_geom_combined.img")
    else:
        simpath = root + "/" + fn.replace(".lbl","_geom_combined.img")

    if os.path.isfile(simpath):
        with open(simpath, "rb") as f:
            sim = np.fromfile(f, np.float32)   
        sim = sim.reshape(rdata.snum,rdata.tnum)
    else:
        sim = np.ones(rdata.dat.shape)

    rdata.set_sim(sim)

    # assign signal info
    rdata.sig = {}
    rdata.sig["signal type"] = "chirp"
    rdata.sig["cf [MHz]"] = 5
    rdata.sig["badwidth [%]"] = 40
    rdata.sig["pulse length [\u03BCs]"] = 200
    rdata.sig["prf [Hz]"] = 20

    # open geom nav file for rgram
    geom_path = fpath.replace(".lbl","_geom.csv")

    # parse nav
    rdata.navdf = navparse.getnav_lrs(geom_path, navcrs, body)

    rdata.set_srfElev(np.repeat(np.nan, rdata.tnum))

    return rdata