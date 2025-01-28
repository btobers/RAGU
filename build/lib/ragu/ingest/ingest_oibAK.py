# RAGU - Radar Analysis Graphical Utility
#
# copyright © 2020 btobers <tobers.brandon@gmail.com>
#
# distributed under terms of the GNU GPL3.0 license
"""
ingest_oibAK is a module developed to ingest NASA OIB-AK radar sounding data. 
primary data format is hdf5, however some older data is still being converted over from .mat format
"""
### imports ###
from ragu.radar import garlic
from ragu.nav import navparse
from ragu.tools import utils
import h5py, fnmatch
import numpy as np
import scipy as sp
import sys

# method to ingest OIB-AK radar hdf5 data format
def read_h5(fpath, navcrs, body):
    rdata = garlic(fpath)
    rdata.fn = fpath.split("/")[-1][:-3]
    rdata.dtype = "oibak"

    # read in .h5 file
    f = h5py.File(rdata.fpath, "r")                      

    # h5 radar data group structure        
    # |-raw
    # |  |-rx0
    # |  |-tx0    
    # |  |-loc0
    # |-ext
    # |  |-nav0
    # |  |-srf0
    # |-drv
    # |  |-proc0
    # |  |-clutter0
    # |  |-pick

    # pull necessary raw group data
    rdata.snum = int(f["raw"]["rx0"].attrs["samplesPerTrace"])                  # samples per trace in rgram
    rdata.tnum = int(f["raw"]["rx0"].attrs["numTrace"])                         # number of traces in rgram 
    rdata.fs = f["raw"]["rx0"].attrs["samplingFrequency"][0]                    # sampling frequency
    rdata.dt = 1/rdata.fs                                                       # sampling interval, sec
    rdata.prf = f["raw"]["tx0"].attrs["pulseRepetitionFrequency"][0]            # pulse repition frequency, Hz
    rdata.nchan = 1

    # pull radar proc and sim arrayss
    rdata.set_dat(f["drv/proc0"][:])                                            # pulse compressed array
    rdata.set_proc(np.abs(rdata.get_dat()))
    if "clutter0" in f["drv"].keys():
        rdata.set_sim(f["drv"]["clutter0"][:])                                  # simulated clutter array

    rdata.set_twtt()
    # assign signal info
    rdata.info["Signal Type"] = f["raw"]["tx0"].attrs["signal"].capitalize() 
    rdata.info["CF [MHz]"] = f["raw"]["tx0"].attrs["centerFrequency"][0] * 1e-6
    if rdata.info["Signal Type"] == "Chirp":
        rdata.info["Badwidth [%]"] = f["raw"]["tx0"].attrs["bandwidth"][0] * 100
        rdata.info["Pulse Length [\u03BCs]"] = f["raw"]["tx0"].attrs["length"][0] * 1e6
    rdata.info["Sampling Frequency [MHz]"] = rdata.fs * 1e-6
    rdata.info["PRF [kHz]"] = rdata.prf * 1e-3

    # parse nav
    rdata.geocrs = navcrs
    rdata.xyzcrs = navparse.xyzsys[body]
    rdata.navdf = navparse.getnav_oibAK_h5(fpath, navcrs, body)
    # pull lidar surface elevation and initilize horizon
    if "srf0" in f["ext"].keys():
        rdata.set_srfElev(dat = f["ext"]["srf0"][:])  
        if "twtt_surf" in f["drv"]["pick"].keys():
            twtt_srf = f["drv"]["pick"]["twtt_surf"][:]
            # replace -1 and -9 null values with np.nan
            twtt_srf[twtt_srf == -1] = np.nan
            twtt_srf[twtt_srf == -9] = np.nan
            arr = utils.twtt2sample(twtt_srf, rdata.dt)
        else:
            arr = utils.twtt2sample(utils.depth2twtt(rdata.navdf["elev"] - rdata.srfElev, rdata.asep, eps_r=1), rdata.dt)
    else:
        arr = np.repeat(np.nan, rdata.tnum)
        rdata.set_srfElev(dat = arr)
    rdata.pick.horizons["srf"] = arr
    rdata.pick.set_srf("srf")

    # # read in bed picks
    # if "twtt_bed" in f["drv"]["pick"].keys():
    #     twtt_bed = f["drv"]["pick"]["twtt_bed"][:]
    #     # replace -1 and -9 null values with np.nan
    #     twtt_bed[twtt_bed == -1] = np.nan
    #     twtt_bed[twtt_bed == -9] = np.nan
    #     arr = utils.twtt2sample(twtt_bed, rdata.dt)
    # else:
    #     arr = np.repeat(np.nan, rdata.tnum)
    # rdata.pick.horizons["bed"] = arr
    

    f.close()                                                   # close the file

    rdata.check_attrs()

    return rdata

# method to ingest .mat files OIB-AK. for older matlab files, sp.io seems to work while h5py does not. for newer files, h5py seems to work while sp.io does not 
def read_mat(fpath, navcrs, body):
    fn = fpath.split("/")[-1]
    print("----------------------------------------")
    print("Loading: " + fn)
    rdata = garlic(fpath)
    rdata.fn = fn[:-4]
    rdata.dtype = "oibak"
    # read in .mat file
    try:
        f = h5py.File(rdata.fpath, "r")
        rdata.snum = int(f["block"]["num_sample"][0])[-1]
        rdata.tnum = int(f["block"]["num_trace"][0])[-1] 
        rdata.dt = float(f["block"]["dt"][0])*2
        rdata.dat = np.array(f["block"]["amp"])
        rdata.set_proc(rdata.dat)

        rdata.navdf = navparse.getnav_oibAK_mat(fpath, navcrs, body)
        rdata.set_sim(np.array(f["block"]["clutter"]))
        twtt_srf = f["block"]["twtt_surf"].flatten()

        f.close()

    except:
        try:
            f = sp.io.loadmat(rdata.fpath)
            rdata.snum = int(f["block"]["num_sample"][0])
            rdata.tnum = int(f["block"]["num_trace"][0])
            rdata.dt = float(f["block"]["dt"][0])*2
            rdata.dat = f["block"]["amp"][0][0]
            rdata.set_proc(rdata.dat)

            rdata.navdf = navparse.getnav_oibAK_mat(fpath, navcrs, body)
            rdata.set_sim(f["block"]["clutter"][0][0])
            twtt_srf = f["block"]["twtt_surf"][0][0].flatten()

        except Exception as err:
            print("ingest Error: " + str(err))
            pass

    rdata.set_twtt()

    if not np.isnan(twtt_srf).all():
        arr = utils.twtt2sample(twtt_srf, rdata.dt)
        rdata.pick.horizons["srf"] = arr
        rdata.pick.srf = "srf"

        # get surface elevation
        arr = rdata.navdf["elev"] - utils.twtt2depth(twtt_srf, rdata.asep, eps_r=1)
        rdata.set_srfElev(dat = arr)

    rdata.check_attrs()

    return rdata