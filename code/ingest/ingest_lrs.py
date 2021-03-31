# RAGU - Radar Analysis Graphical Utility
#
# copyright © 2020 btobers <tobers.brandon@gmail.com>
#
# distributed under terms of the GNU GPL3.0 license
"""
ingest_lrs is a module developed to ingest JAXA KAGUYA (SELENE) Lunar Radar Sounder (LRS) data.
"""
### imports ###
from radar import radar
from nav import navparse
from tools import utils
import numpy as np
import os, sys

# method to read KAGUYA (SELENE) LRS SAR data
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
    # get number of traces (file records in lbl file) and samples per trace
    rdata.tnum = int(lbl[19].split('=')[1])
    rdata.snum = 1000

    rdata.fn = fn.rstrip(".lbl")
    rdata.dtype = "lrs"
    # convert binary .img RGRAM to numpy array - data begins after 55 bytes of header info
    with open(rdata.fpath, "rb") as f:
        f.seek(rdata.tnum*55)
        data = f.read(rdata.tnum*rdata.snum)
        rdata.dat = np.frombuffer(data, np.uint8)     
    l = len(rdata.dat)

    rdata.dt = 305.17578125e-09
    rdata.prf = 20
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
    rdata.info = {}
    rdata.info["Signal Type"] = "Chirp"
    rdata.info["CF [MHz]"] = 5
    rdata.info["Bandwidth [%]"] = 40
    rdata.info["Pulse Length [\u03BCs]"] = 200
    rdata.info["PRF [Hz]"] = rdata.prf

    # open geom nav file for rgram
    geom_path = fpath.replace(".lbl","_geom.csv")

    # parse nav - use spice derived nav, not header data due to header data issues
    rdata.navdf = navparse.getnav_lrs(geom_path, navcrs, body)

    rdata.set_srfElev(np.repeat(np.nan, rdata.tnum))

    return rdata