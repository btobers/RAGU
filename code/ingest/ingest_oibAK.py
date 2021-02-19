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
from radar import radar
from nav import navparse
from tools import utils
import h5py, fnmatch
import numpy as np
import scipy as sp
import sys

# method to ingest OIB-AK radar hdf5 data format
def read_h5(fpath, navcrs, body):
    rdata = radar(fpath)
    rdata.fn = fpath.split("/")[-1][:-3]
    rdata.dtype = "oibak"

    # read in .h5 file
    print("----------------------------------------")
    print("Loading: " + rdata.fn)
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
    rdata.dt = 1/ f["raw"]["rx0"].attrs["samplingFrequency"]                    # sampling interval, sec
    rdata.nchan = 1

    # pull radar proc and sim arrays
    rdata.dat = f["drv/proc0"][:]                                               # pulse compressed array
    rdata.set_proc(np.abs(rdata.dat))
    if "clutter0" in f["drv"].keys():
        rdata.set_sim(f["drv"]["clutter0"][:])                                  # simulated clutter array
    else:
        rdata.set_sim(np.ones(rdata.dat.shape))                                 # empty clutter array if no sim exists

    # assign signal info
    rdata.sig = {}
    rdata.sig["Signal Type"] = f["raw"]["tx0"].attrs["signal"].decode().capitalize() 
    rdata.sig["CF [MHz]"] = f["raw"]["tx0"].attrs["centerFrequency"] * 1e-6
    if rdata.sig["Signal Type"] == "chirp":
        rdata.sig["Badwidth [%]"] = f["raw"]["tx0"].attrs["bandwidth"] * 100
        rdata.sig["Pulse Length [\u03BCs]"] = f["raw"]["tx0"].attrs["length"] * 1e6
    rdata.sig["PRF [kHz]"] = f["raw"]["tx0"].attrs["pulseRepetitionFrequency"] * 1e-3

    # parse nav
    rdata.navdf = navparse.getnav_oibAK_h5(fpath, navcrs, body)
    
    # pull lidar surface elevation and initilize horizon
    if "srf0" in f["ext"].keys():
        rdata.set_surfElev(f["ext"]["srf0"][:])  
        if "twtt_surf" in f["drv"]["pick"].keys():
            rdata.pick.horizons["surface"] = utils.twtt2sample(f["drv"]["pick"]["twtt_surf"][:], rdata.dt)
        else:
            rdata.pick.horizons["surface"] = utils.twtt2sample(utils.depth2twtt(rdata.navdf["elev"] - rdata.surfElev, eps_r=1), rdata.dt)
    else:
        rdata.set_surfElev(np.repeat(np.nan, rdata.tnum))
        rdata.pick.horizons["surface"] = np.repeat(np.nan, rdata.tnum)

    # # pull lidar surface elevation
    # if "srf0" in f["ext"].keys():
    #     rdata.set_surfElev(f["ext"]["srf0"][:])                                  # surface elevation from lidar, averaged over radar first fresnel zone per trace (see code within /zippy/MARS/code/xped/hfProc/ext)
    #     # read in existing surface pick
    #     if "twtt_surf" in f["drv"]["pick"].keys():
    #         rdata.pick.existing_twttSurf = f["drv"]["pick"]["twtt_surf"][:]
    #     else:
    #         # calculate twtt_surf
    #         rdata.pick.existing_twttSurf = utils.depth2twtt(rdata.navdf["elev"] - rdata.surfElev, eps_r=1)
    # create empty arrays to hold surface elevation and twtt otherwise
    # else:
    #     rdata.set_surfElev(np.repeat(np.nan, rdata.tnum))

    # read in existing subsurface picks
    num_file_pick_lyr = len(fnmatch.filter(f["drv"]["pick"].keys(), "twtt_subsurf*"))
    if num_file_pick_lyr > 0:
        # iterate through any existing subsurface pick layers to import
        for _i in range(num_file_pick_lyr):
            rdata.pick.existing_twttSubsurf[str(_i)] = np.array(f["drv"]["pick"]["twtt_subsurf" + str(_i)])

    # initialize surface pick
    rdata.pick.current_surf = np.repeat(np.nan, rdata.tnum)

    f.close()                                                   # close the file

    # # temporary fix to roll array for impulse data to line up with surface - find offset by windowing around lidar surface
    # if (rdata.sig["signal type"] == "impulse") and (not np.isnan(rdata.pick.existing_twttSurf).all()):
    #     lidarsrf = utils.twtt2sample(rdata.pick.existing_twttSurf, rdata.dt)
    #     pksrf = utils.pkampwind(rdata.dat, lidarsrf, 60)
    #     avoffset = np.nanmean(lidarsrf - pksrf)
    #     rdata.dat = np.roll(rdata.dat, int(round(avoffset)), axis=0)
    #     rdata.set_proc(np.abs(rdata.dat))

    return rdata

# method to ingest .mat files OIB-AK. for older matlab files, sp.io seems to work while h5py does not. for newer files, h5py seems to work while sp.io does not 
def read_mat(fpath, navcrs, body):
    fn = fpath.split("/")[-1]
    print("----------------------------------------")
    print("Loading: " + fn)
    rdata = radar(fpath)
    rdata.fn = fn[:-4]
    rdata.dtype = "oibak"
    # read in .mat file
    try:
        f = h5py.File(rdata.fpath, "r")
        rdata.snum = int(f["block"]["num_sample"][0])[-1]
        rdata.tnum = int(f["block"]["num_trace"][0])[-1] 
        rdata.dt = float(f["block"]["dt"][0])
        rdata.dat = np.array(f["block"]["amp"])
        rdata.set_proc(rdata.dat)

        rdata.navdf = navparse.getnav_oibAK_mat(fpath, navcrs, body)
        rdata.set_sim(np.array(f["block"]["clutter"]))

        rdata.pick.existing_twttSurf = f["block"]["twtt_surf"].flatten()
        f.close()

    except:
        try:
            f = sp.io.loadmat(rdata.fpath)
            rdata.snum = int(f["block"]["num_sample"][0])
            rdata.tnum = int(f["block"]["num_trace"][0])
            rdata.dt = float(f["block"]["dt"][0])
            rdata.dat = f["block"]["amp"][0][0]
            rdata.set_proc(rdata.dat)

            rdata.navdf = navparse.getnav_oibAK_mat(fpath, navcrs, body)
            rdata.set_sim(f["block"]["clutter"][0][0])

            rdata.pick.existing_twttSurf = f["block"]["twtt_surf"][0][0].flatten()

        except Exception as err:
            print("ingest Error: " + str(err))
            pass

    # calculate surface elevation 
    dist = utils.twtt2depth(rdata.pick.existing_twttSurf, eps_r=1)
    rdata.set_surfElev(rdata.navdf["hgt"].to_numpy() - dist)

    # initialize surface pick
    rdata.pick.current_surf = np.repeat(np.nan, rdata.tnum)
    
    return rdata