# RAGU - Radar Analysis Graphical Utility
#
# copyright © 2020 btobers <tobers.brandon@gmail.com>
#
# distributed under terms of the GNU GPL3.0 license
"""
ingest_rimfax is a module developed to ingest NASA's Perseverance Radar Imager for Mars' subsurface experiment (RIMFAX) data.
"""
### imports ###
from ragu.radar import garlic
from ragu.nav import navparse
from ragu.tools import utils
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
## for fn in glob.glob('rimfax*.csv'):
##     f = pd.read_csv(fn, header=0)
##     for m,n in zip(mode,name):
##         f_ = f.loc[(f["record_type"]==0) & (f["config_id"]==m)]
##         f_.to_csv(fn[:-4]+'_'+n+'.csv')
####

def read(fpath, navcrs, body):
    rdata = garlic(fpath)
    rdata.fn = fpath.split("/")[-1][:-4]
    rdata.dtype = "rimfax"

    # only read necessary data from file
    f = pd.read_csv(rdata.fpath, header=0)
    f = f.loc[f["record_type"]==0]                                                      # only retain active sounding
    idx = f.columns.get_loc("s0001")
    dat = np.array(f.iloc[:,idx:])                                                      # parse actual data
    # find traces with all null samples
    filt = ~np.isnan(dat).all(axis=1)                                                   
    f = f.iloc[filt,:]
    dat = dat[filt,:]

    rdata.set_dat(np.array(dat).T)                                                      # transpose 
    rdata.set_proc(np.abs(rdata.get_dat()))

    rdata.snum, rdata.tnum =  dat.shape                                                 # snum, tnum
    rdata.dt = np.mean(f["sample_time_increment"])*1e-9                                 # sampling interval, sec - don't know if it's necessary to use the mean. i wouldn't expect the value doesn't change, but not sure

    rdata.prf = 1 / rdata.dt                                                           # pulse repitition frequency
    rdata.nchan = 1
    rdata.set_twtt()

    # parse nav
    rdata.geocrs = navcrs
    rdata.xyzcrs = navparse.xyzsys[body]
    rdata.navdf = navparse.getnav_rimfax(fpath, navcrs, body)
    rdata.set_srfElev(dat = np.repeat(np.nan, rdata.tnum))

    rdata.info["PRF [kHz]"] = rdata.prf * 1e-3

    rdata.check_attrs()
    return rdata