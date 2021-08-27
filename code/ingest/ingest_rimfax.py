# RAGU - Radar Analysis Graphical Utility
#
# copyright © 2020 btobers <tobers.brandon@gmail.com>
#
# distributed under terms of the GNU GPL3.0 license
"""
ingest_rimfax is a module developed to ingest NASA's Perseverance Radar Imager for Mars' subsurface experiment (RIMFAX) data.
"""
### imports ###
from radar import garlic
from nav import navparse
from tools import utils
import h5py, fnmatch
import pandas as pd
import numpy as np
import sys
import matplotlib.pyplot as plt
# method to ingest RIMFAX radar data
def read(fpath, navcrs, body):
    rdata = garlic(fpath)
    rdata.fn = fpath.split("/")[-1][:-4]
    rdata.dtype = "rimfax"

    print("----------------------------------------")
    print("Loading: " + rdata.fn)

    # only read necessary data from file
    f = pd.read_csv(rdata.fpath, header=0, skiprows=range(1,6))
    f = f.loc[f["record_type"]==0]
    rdata.set_dat(np.array(f.iloc[:,90:]).T)
    rdata.set_proc(np.abs(rdata.get_dat()))
    rdata.set_sim(np.ones(rdata.dat.shape))  

    rdata.snum =  np.max(f["n_samples"])                                                # samples per trace in rgram
    rdata.tnum = len(f)                                                                 # number of traces in rgram 
    rdata.dt = np.mean(f["sample_time_increment"])                                      # sampling interval, sec

    rdata.prf = 1 / rdata.dt                                                           # pulse repitition frequency
    rdata.nchan = 1

    # parse nav
    rdata.navdf = navparse.getnav_rimfax(fpath, navcrs, body)
    print(rdata.navdf)
    rdata.set_srfElev(dat = np.repeat(np.nan, rdata.tnum))

    rdata.info["PRF [kHz]"] = rdata.prf * 1e-3


    return rdata