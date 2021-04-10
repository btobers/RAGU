# RAGU - Radar Analysis Graphical Utility
#
# copyright © 2020 btobers <tobers.brandon@gmail.com>
#
# distributed under terms of the GNU GPL3.0 license
"""
ingest_cresis_rds is a module developed to ingest CReSIS snow accumulation radar data. 
"""
### imports ###
from radar import garlic
from nav import navparse
from tools import utils
import h5py, fnmatch
import numpy as np
import sys
import matplotlib.pyplot as plt
# method to ingest CReSIS snow radar data
def read_mat(fpath, navcrs, body):
    rdata = garlic(fpath)
    rdata.fn = fpath.split("/")[-1][:-4]
    rdata.dtype = "cresis_snow"
    f = h5py.File(rdata.fpath, "r")                      

    # assign signal info
    rdata.info["System"] = str(f["param_records"]["radar_name"][:], 'utf-16')
    if "snow" not in rdata.info["System"]:
        raise ValueError("Not snow radar data")
        return

    print("----------------------------------------")
    print("Loading: " + rdata.fn)

    rdata.dat = np.array(f["Data"][:]).T
    rdata.set_proc(np.abs(rdata.dat))
    rdata.set_sim(np.ones(rdata.dat.shape))  

    rdata.snum = rdata.dat.shape[0]                                                 # samples per trace in rgram
    rdata.tnum = rdata.dat.shape[1]                                                 # number of traces in rgram 
    rdata.dt = np.mean(np.diff(f["Time"]))                                          # sampling interval, sec
    rdata.prf = f["param_records"]["radar"]["prf"][0][0]                            # pulse repitition frequency
    rdata.nchan = 1

    # parse nav
    rdata.navdf = navparse.getnav_cresis_mat(fpath, navcrs, body)

    # pull surface elevation and initilize horizon
    rdata.set_srfElev(f["Surface"][:].flatten()) 

    rdata.pick.horizons["srf"] = utils.twtt2sample(f["Surface"][:].flatten(), rdata.dt)
    rdata.set_srfElev(rdata.navdf["elev"] - utils.twtt2depth(rdata.pick.horizons["srf"], eps_r=1))
    rdata.pick.srf = "srf"

    rdata.info["PRF [kHz]"] = rdata.prf * 1e-3

    f.close()                                                   # close the file

    return rdata