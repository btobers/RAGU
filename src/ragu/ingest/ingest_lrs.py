# RAGU - Radar Analysis Graphical Utility
#
# copyright © 2020 btobers <tobers.brandon@gmail.com>
#
# distributed under terms of the GNU GPL3.0 license
"""
ingest_lrs is a module developed to ingest JAXA KAGUYA (SELENE) Lunar Radar Sounder (LRS) data.
"""
### imports ###
from ragu.radar import garlic
from ragu.nav import navparse
from ragu.tools import utils
import numpy as np
import os, sys

# method to read KAGUYA (SELENE) LRS SAR data
def read(fpath, simpath, navcrs, body):
    rdata = garlic(fpath)
    rdata.fn = fpath.split("/")[-1][:-4]
    rdata.dtype = "lrs"
    root = os.path.dirname(fpath)

    # get number of traces (file records in lbl file) and samples per trace
    with open(fpath.replace(".img", ".lbl"),'r') as f:
        lbl = f.read().split('\n')
    rdata.tnum = int(lbl[19].split('=')[1])
    rdata.snum = 1000

    # convert binary .img RGRAM to numpy array - data begins after 55 bytes of header info
    with open(rdata.fpath, "rb") as f:
        f.seek(rdata.tnum*55)
        tmp = f.read(rdata.tnum*rdata.snum)
        dat = np.frombuffer(tmp, np.uint8)
    l = len(dat)

    rdata.dt = 305.17578125e-09
    rdata.prf = 20
    rdata.nchan = 1
    rdata.set_dat(dat.reshape(rdata.snum,rdata.tnum))
    rdata.set_proc(rdata.get_dat())
    
    # convert binary .img clutter sim product to numpy array
    if simpath:
        simpath = simpath + "/" + rdata.fn + "_geom_combined.img"
    else:
        simpath = root + "/" + rdata.fn + "_geom_combined.img"

    if os.path.isfile(simpath):
        with open(simpath, "rb") as f:
            sim = np.fromfile(f, np.float32)   
        sim = sim.reshape(rdata.snum,rdata.tnum)
        rdata.set_sim(sim)

    rdata.set_twtt()

    # assign signal info
    rdata.info = {}
    rdata.info["Signal Type"] = "Chirp"
    rdata.info["CF [MHz]"] = 5
    rdata.info["Bandwidth [%]"] = 40
    rdata.info["Pulse Length [\u03BCs]"] = 200
    rdata.info["PRF [Hz]"] = rdata.prf

    # open geom nav file for rgram - Michael Christoffersen post-processed geom files using SPICE trajectory. 
    # if this is not available, use binary stored nav.
    geom_path = fpath.replace(".lbl","_geom.csv")
    if not os.path.isfile(geom_path):
        geom_path = rdata.fpath

    # parse nav - use spice derived nav, not header data due to header data issues
    rdata.geocrs = navcrs
    rdata.xyzcrs = navparse.xyzsys[body]
    rdata.navdf = navparse.getnav_lrs(geom_path, navcrs, body, rdata.tnum)

    rdata.set_srfElev(dat = np.repeat(np.nan, rdata.tnum))

    rdata.check_attrs()

    return rdata