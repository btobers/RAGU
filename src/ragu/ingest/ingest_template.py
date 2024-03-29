# RAGU - Radar Analysis Graphical Utility
#
# copyright © 2020 btobers <tobers.brandon@gmail.com>
#
# distributed under terms of the GNU GPL3.0 license
"""
ingest_template is a RAGU data ingest template. Follow this basic template format and modify to read your radar data type.

NOTE: ingest/__init__.py must also be modified after creating a new ingester for RAGU to be able to ingest your data type 
ALSO: nav/navparse.py will need an additional method for reading your navigation data
"""
### necessary imports, different data types may require additional ###
from ragu.radar import garlic
from ragu.nav import navparse
from ragu.tools import utils
import h5py, fnmatch
import numpy as np
import scipy as sp
import sys

# method to ingest your data
def read_dat(fpath, navcrs, body):
    # initialize the radar data object - garlic() takes the data file path
    rdata = garlic(fpath)

    # define the rdar data file name - str
    rdata.fn = fpath.split("/")[-1][:-3]

    # name the data type - str
    rdata.dtype = "blah"

    # read in .h5 file
    f = h5py.File(rdata.fpath, "r")                      

    ############################################################################
    #### necessary radar attributes - modify these based on your data type   ###
    ############################################################################
    rdata.snum = None       # samples per trace in rgram, int
    rdata.tnum = None       # number of traces in rgram, int
    rdata.fs =  None        # sampling frequency (Hz), float
    rdata.prf = None        # pulse repition frequency (Hz), float
    data = None             # 2D radar data array of shape ((rdata.snum x rdata.tnu,)) - pulse compressed if chirped data- this should be amplitude units, float

    # parse nav - you may need to create a navparse method for reading your nav data (replace "getnav" with the name of your nav parser method)
    rdata.geocrs = navcrs
    rdata.xyzcrs = navparse.xyzsys[body]
    rdata.navdf = navparse.getnav(fpath, navcrs, body)
    ############################################################################


    ############################################################################
    ############################# optional changes #############################
    ############################################################################
    rdata.nchan = 1     # number of data channels - don't need to touch this unless multichannel data, int
    sim = None              # 2D radar clutter simulation of shape ((rdata.snum x rdata.tnu,)) - this should be amplitude units, float
    # assign signal info - add more if you'd like. These show up on a banner at the bottom of the RAGU GUI window
    rdata.info["Signal Type"] = 'Impulse'
    rdata.info["CF [MHz]"] =  5 * 1e-6
    rdata.info["Pulse Length [\u03BCs]"] = 2.5 * 1e6
    rdata.info["Sampling Frequency [MHz]"] = rdata.fs * 1e-6
    rdata.info["PRF [kHz]"] = rdata.prf * 1e-3
    ############################################################################




    # shouldn't need to touch these after changing the above
    rdata.dt = 1/rdata.fs               # sampling interval, sec
    rdata.set_dat(data)                 # assign amplitude data array as input radar data
    rdata.set_proc(rdata.get_dat())     # this stores a processed data array - data is dB'd for display purposes
    if sim:
        rdata.set_sim(sim)              # clutter sim array

    rdata.set_twtt()                    # get twtt for fast-time axis
    rdata.check_attrs()                 # check radar data attributes to make sure everything is garlicy

    return rdata