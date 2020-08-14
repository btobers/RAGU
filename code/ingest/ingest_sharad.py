"""
ingest_sharad is a module developed to ingest NASA MRO-SHARAD FPB radar sounding data. 
data format is binary 32-bit floating point pulse compressed amplitude data acquired from the PDS
"""
### imports ###
from radar import radar
from nav import navparse
from tools import utils
import numpy as np
import os

# method to read PDS SHARAD USRDR data
def read(fpath, simpath, navcrs, body):
    fn = fpath.split("/")[-1]
    print("----------------------------------------")
    print("Loading: " + fn)
    rdata = radar(fpath)
    rdata.fn = fn.rstrip(fn.split("_")[-2])
    rdata.dtype = "sharad"
    # convert binary .img PDS RGRAM to numpy array
    # reshape array with 3600 lines
    dtype = np.dtype("float32")     
    with open(fpath, "rb") as f:
        rdata.dat = np.fromfile(f, dtype)     
    l = len(rdata.dat)

    rdata.snum = 3600
    rdata.tnum = int(len(rdata.dat)/rdata.snum)
    rdata.dt = .0375e-6
    rdata.dat = rdata.dat.reshape(rdata.snum,rdata.tnum)
    rdata.set_proc(rdata.dat)
    
    # convert binary .img clutter sim product to numpy array
    simpath = simpath + "/" + fn.replace("rgram","geom_combined")
    if os.path.isfile(simpath):
        with open(simpath, "rb") as f:
            sim = np.fromfile(f, dtype)   
        sim = sim.reshape(rdata.snum,rdata.tnum)
    else:
        sim = np.ones(rdata.dat.shape)
    
    rdata.set_sim(sim)

    # open geom nav file for rgram
    geom_path = fpath.replace("rgram","geom").replace("img","tab")

    # parse nav
    rdata.navdf = navparse.getnav_sharad(geom_path, navcrs, body)

    rdata.elev_gnd = np.repeat(np.nan, rdata.tnum)

    # initialize surface pick
    rdata.pick.current_surf = np.repeat(np.nan, rdata.tnum)

    return rdata