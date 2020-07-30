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
def read(fpath, navcrs, body):
    print("----------------------------------------")
    print("Loading: " + fpath.split("/")[-1])
    rdata = radar(fpath.split("/")[-1])
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
    rdata.proc_data = rdata.dat
    
    # convert binary .img clutter sim product to numpy array
    clutpath = fpath.replace("rgram","geom_combined")
    if os.path.isfile(clutpath):
        with open(clutpath, "rb") as f:
            rdata.clut = np.fromfile(f, dtype)   
        rdata.clut = rdata.clut.reshape(rdata.snum,rdata.tnum)
    else:
        rdata.clut = np.ones(rdata.dat.shape)

    # open geom nav file for rgram
    geom_path = fpath.replace("rgram","geom").replace("img","tab")

    # parse nav
    rdata.navdf = navparse.getnav_sharad(geom_path, navcrs, body)

    rdata.elev_gnd = np.repeat(np.nan, rdata.tnum)

    return rdata