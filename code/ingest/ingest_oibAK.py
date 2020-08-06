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

# method to ingest OIB-AK radar hdf5 data format
def read_h5(fpath, navcrs, body):
    print("----------------------------------------")
    print("Loading: " + fpath.split("/")[-1])
    rdata = radar(fpath)
    rdata.dtype = "oibak"
    # read in .h5 file
    f = h5py.File(rdata.fpath, "r")                      

    # h5 radar data group structure        
    # |-raw
    # |  |-rx0
    # |  |-loc0
    # |-ext
    # |  |-nav0
    # |  |-srf0
    # |-drv
    # |  |-proc0
    # |  |-clutter0
    # |  |-pick

    # pull necessary raw group data
    rdata.snum = f["raw"]["rx0"].attrs["samplesPerTrace"]               # samples per trace in rgram
    rdata.tnum = f["raw"]["rx0"].attrs["numTrace"]                      # number of traces in rgram 
    rdata.dt = 1/ f["raw"]["rx0/"].attrs["samplingFrequency-Hz"]        # sampling interval, sec

    # pull necessary drv group data
    rdata.dat = f["drv/proc0"][:]                                       # pulse compressed array
    rdata.set_proc(np.abs(rdata.dat))

    # parse nav
    rdata.navdf = navparse.getnav_oibAK_h5(fpath, navcrs, body)
    
    # pull lidar surface elevation if possible
    if "srf0" in f["ext"].keys():
        rdata.elev_gnd = f["ext"]["srf0"][:]                            # surface elevation from lidar, averaged over radar first fresnel zone per trace (see code within /zippy/MARS/code/xped/hfProc/ext)
    # create empty arrays to hold surface elevation and twtt otherwise
    else:
        rdata.elev_gnd = np.repeat(np.nan, rdata.tnum)

    if "clutter0" in f["drv"].keys():
        rdata.clut = rdata.dBscale(f["drv"]["clutter0"][:])             # simulated clutter array
    else:
        rdata.clut = np.ones(rdata.dat.shape)                           # empty clutter array if no sim exists
    
    # generate image pyramids for dynamic rendering
    rdata.genPyramids()

    # read in existing surface picks
    if "twtt_surf" in f["drv"]["pick"].keys():
        rdata.pick.existing_twttSurf =f["drv"]["pick"]["twtt_surf"][:]

    # read in existing subsurface picks
    num_file_pick_lyr = len(fnmatch.filter(f["drv"]["pick"].keys(), "twtt_subsurf*"))
    if num_file_pick_lyr > 0:
        # iterate through any existing subsurface pick layers to import
        for _i in range(num_file_pick_lyr):
            rdata.pick.existing_twttSubsurf[str(_i)] = np.array(f["drv"]["pick"]["twtt_subsurf" + str(_i)])

    # initialize surface pick
    rdata.pick.current_surf = np.repeat(np.nan, rdata.tnum)

    f.close()                                                   # close the file

    return rdata

# method to ingest .mat files OIB-AK. for older matlab files, sp.io seems to work while h5py does not. for newer files, h5py seems to work while sp.io does not 
def read_mat(fpath, navcrs, body):
    print("----------------------------------------")
    print("Loading: " + fpath.split("/")[-1])
    rdata = radar(fpath)
    try:
        f = h5py.File(rdata.fpath, "r")
        rdata.snum = int(f["block"]["num_sample"][0])[-1]
        rdata.tnum = int(f["block"]["num_trace"][0])[-1] 
        rdata.dt = float(f["block"]["dt"][0])
        rdata.dat = np.array(f["block"]["amp"])
        rdata.set_proc(rdata.dat)

        rdata.navdf = navparse.getnav_oibAK_mat(fpath, navcrs, body)
        rdata.clut = rdata.dBscale(np.array(f["block"]["clutter"]))

        rdata.pick.existing.twtt_surf = f["block"]["twtt_surf"].flatten()
        f.close()

    except:
        try:
            f = sp.io.loadmat(rdata.fpath)
            rdata.snum = int(f["block"]["num_sample"][0])
            rdata.tnum = int(f["block"]["num_trace"][0])
            rdata.dt = float(f["block"]["dt"][0])
            rdata.dat = f["block"]["amp"][0][0]
            rdata.proc(rdata.dat)

            rdata.navdf = navparse.getnav_oibAK_mat(fpath,navcrs,body)
            rdata.clut = rdata.dBscale(f["block"]["clutter"][0][0])

            rdata.pick.existing.twtt_surf = f["block"]["twtt_surf"][0][0].flatten().astype(np.float64)

        except Exception as err:
            print("ingest Error: " + str(err))
            pass

    print("----------------------------------------")
    print("Loading: " + fpath.split("/")[-1])
    
    # calculate surface elevation 
    rdata.elev_gnd = rdata.navdf["elev"] - (rdata.pick.existing.twtt_surf*C/2)

    return rdata