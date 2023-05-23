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
# method to ingest RIMFAX radar data from the PDS

###
#  data files should first be split up into separate files for each mode of active sounding - use the following commented code to do this:
## mode=[26,78,214]
## name=['shallow','surface','deep']
## for fn in glob.glob('*.csv'):
##     f = pd.read_csv(fn, header=0)
##     for m,n in zip(mode,name):
##         f = f.loc[(f["record_type"]==0) & (f["config_id"]==m)]
##         f.to_csv(fn[:-4]+'_'+n+'.csv')
####

def read(fpath, navcrs, body):
    rdata = garlic(fpath)
    rdata.fn = fpath.split("/")[-1][:-4]
    rdata.dtype = "rimfax"

    # only read necessary data from file
    f = pd.read_csv(rdata.fpath, header=0, skiprows=range(1,6))
    f = f.loc[f["record_type"]==0]
    rdata.set_dat(np.array(f.iloc[:,90:]).T)
    rdata.set_proc(np.abs(rdata.get_dat()))

    rdata.snum =  np.max(f["n_samples"])                                                # samples per trace in rgram
    rdata.tnum = len(f)                                                                 # number of traces in rgram 
    rdata.dt = np.mean(f["sample_time_increment"])                                      # sampling interval, sec

    rdata.prf = 1 / rdata.dt                                                           # pulse repitition frequency
    rdata.nchan = 1
    rdata.set_twtt()

    # parse nav
    rdata.navdf = navparse.getnav_rimfax(fpath, navcrs, body)
    rdata.set_srfElev(dat = np.repeat(np.nan, rdata.tnum))

    rdata.info["PRF [kHz]"] = rdata.prf * 1e-3

    rdata.check_attrs()

    return rdata