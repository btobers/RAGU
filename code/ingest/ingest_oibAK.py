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

### method to ingest OIB-AK radar hdf5 data format ###
def read_h5(fpath, navcrs, body):
    print("----------------------------------------")
    print("Loading: " + fpath.split("/")[-1])
    rdata = radar(fpath.split("/")[-1])
    # read in .h5 file
    f = h5py.File(fpath, "r")                      

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
    rdata.dat = f["drv/proc0"][:]                                      # pulse compressed array
    rdata.proc_data = np.abs(rdata.dat)

    # parse nav
    rdata.navdf = navparse.getnav_oibAK_h5(fpath, navcrs, body)
    
    # pull lidar surface elevation if possible
    if "srf0" in f["ext"].keys():
        rdata.elev_gnd = f["ext"]["srf0"][:]                          # surface elevation from lidar, averaged over radar first fresnel zone per trace (see code within /zippy/MARS/code/xped/hfProc/ext)
    # create empty arrays to hold surface elevation and twtt otherwise
    else:
        rdata.elev_gnd = np.repeat(np.nan, rdata.tnum)

    if "clutter0" in f["drv"].keys():
        rdata.clut = f["drv"]["clutter0"][:]                       # simulated clutter array
    else:
        rdata.clut = np.ones(rdata.dat.shape)                            # empty clutter array if no sim exists
    
    # read in existing surface picks
    if "twtt_surf" in f["drv"]["pick"].keys():
        rdata.pick.existing.twtt_surf =f["drv"]["pick"]["twtt_surf"][:]

    # read in existing subsurface picks
    num_file_pick_lyr = len(fnmatch.filter(f["drv"]["pick"].keys(), "twtt_subsurf*"))
    if num_file_pick_lyr > 0:
        # iterate through any existing subsurface pick layers to import
        for _i in range(num_file_pick_lyr):
            rdata.pick.existing.twtt_subsurf[str(_i)] = np.array(f["drv"]["pick"]["twtt_subsurf" + str(_i)])

    f.close()                                                   # close the file

    return rdata

def read_mat(fpath, navcrs, body):
# method to ingest .mat files. for older matlab files, sp.io works and h5py does not. for newer files, h5py works and sp.io does not 
    rdata = radar(fpath.split("/")[-1])
    try:
        f = h5py.File(fpath, "r")
        rdata.snum = int(f["block"]["num_sample"][0])[-1]
        rdata.tnum = int(f["block"]["num_trace"][0])[-1] 
        rdata.dt = float(f["block"]["dt"][0])
        rdata.dat = np.array(f["block"]["amp"])
        rdata.proc_data = rdata.dat

        rdata.navdf = navparse.getnav_oibAK_mat(fpath, navcrs, body)
        rdata.clut = np.array(f["block"]["clutter"])

        rdata.pick.existing.twtt_surf = f["block"]["twtt_surf"].flatten()
        f.close()

    except:
        try:
            f = sp.io.loadmat(fpath)
            rdata.snum = int(f["block"]["num_sample"][0])
            rdata.tnum = int(f["block"]["num_trace"][0])
            rdata.dt = float(f["block"]["dt"][0])
            rdata.dat = f["block"]["amp"][0][0]
            rdata.proc_data = rdata.dat

            rdata.navdf = navparse.getnav_oibAK_mat(fpath,navcrs,body)
            rdata.clut = f["block"]["clutter"][0][0]

            rdata.pick.existing.twtt_surf = f["block"]["twtt_surf"][0][0].flatten().astype(np.float64)

        except Exception as err:
            print("ingest Error: " + str(err))
            pass

    print("----------------------------------------")
    print("Loading: " + fpath.split("/")[-1])
    
    # calculate surface elevation 
    rdata.elev_gnd = rdata.navdf["elev"] - (rdata.pick.existing.twtt_surf*C/2)

    return rdata