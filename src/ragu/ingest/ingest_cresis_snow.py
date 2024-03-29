# RAGU - Radar Analysis Graphical Utility
#
# copyright © 2020 btobers <tobers.brandon@gmail.com>
#
# distributed under terms of the GNU GPL3.0 license
"""
ingest_cresis_rds is a module developed to ingest CReSIS snow accumulation radar data. 
"""
### imports ###
from ragu.radar import garlic
from ragu.nav import navparse
from ragu.tools import utils
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

    rdata.set_dat(np.array(f["Data"][:].T))
    rdata.set_proc(np.abs(rdata.get_dat()))
    rdata.snum = rdata.dat.shape[0]                                                 # samples per trace in rgram
    rdata.tnum = rdata.dat.shape[1]                                                 # number of traces in rgram 
    rdata.set_twtt(arr = f["Time"][:].flatten())                                    # set two way travel time
    rdata.dt = np.diff(rdata.get_twtt())[0]                                         # sampling interval, sec
    rdata.prf = f["param_records"]["radar"]["prf"][0][0]                            # pulse repitition frequency
    rdata.nchan = 1

    # store truncated samples
    try:
        rdata.truncs = f["Truncate_Bins"][:].flatten()[0].astype(int)
    except:
        rdata.truncs = 0

    # parse nav
    rdata.geocrs = navcrs
    rdata.xyzcrs = navparse.xyzsys[body]
    rdata.navdf = navparse.getnav_cresis_mat(fpath, navcrs, body)

    # pull surface two-way travel time and initilize horizon
    rdata.pick.srf = "srf"
    # get two-way travel times to lidar surface from CReSIS snow radar data
    twtt_surf = f["Surface"][:].flatten()
    rdata.pick.horizons["srf"] = utils.twtt2sample(twtt_surf, rdata.dt)
    # account for truncated samples above row zero in radargram
    rdata.pick.horizons["srf"] -= rdata.truncs
    rdata.set_srfElev() 

    # store pulse rep
    rdata.info["PRF [kHz]"] = rdata.prf * 1e-3

    f.close()                                                   # close the file

    rdata.check_attrs()

    return rdata