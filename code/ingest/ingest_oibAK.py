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

    # parse nav
    rdata.navdf = navparse.getnav_oibAK(fpath, navcrs, body)
    
    # pull lidar surface elevation if possible
    if "srf0" in f["ext"].keys():
        rdata.elev_gnd = f["ext"]["srf0"][:]                          # surface elevation from lidar, averaged over radar first fresnel zone per trace (see code within /zippy/MARS/code/xped/hfProc/ext)
    # create empty arrays to hold surface elevation and twtt otherwise
    else:
        rdata.elev_gnd = np.repeat(np.nan, rdata.tnum)

    # pull necessary drv group data
    rdata.dat = f["drv/proc0"][:]                                      # pulse compressed array
    rdata.proc_data = np.abs(rdata.dat)

    if "clutter0" in f["drv"].keys():
        rdata.clut = f["drv"]["clutter0"][:]                       # simulated clutter array
    else:
        rdata.clut = np.ones(rdata.dat.shape)                            # empty clutter array if no sim exists
    
    # read in existing surface picks
    if "twtt_surf" in f["drv"]["pick"].keys():
        rdata.pick.existing["twtt_surf"] =f["drv"]["pick"]["twtt_surf"][:]

    # read in existing subsurface picks
    num_file_pick_lyr = len(fnmatch.filter(f["drv"]["pick"].keys(), "twtt_subsurf*"))
    if num_file_pick_lyr > 0:
        # iterate through any existing subsurface pick layers to import
        for _i in range(num_file_pick_lyr):
            rdata.pick.existing["twtt_subsurf" + str(_i)] = np.array(f["drv"]["pick"]["twtt_subsurf" + str(_i)])

    f.close()                                                   # close the file

    # replace potential erroneous twtt_surf values with nan
    # get indices where twtt_surf is not nan
    # idx = np.logical_not(np.isnan(pick["twtt_surf"]))
    # pick["twtt_surf"][np.where(pick["twtt_surf"][idx] > rdata.snum*rdata.dt)[0]] = np.nan
    # pick["twtt_surf"][np.where(pick["twtt_surf"][idx] <= rdata.dt)[0]] = np.nan
    
    # # get indices of twtt_surf
    # rdata.surf = utils.twtt2sample(pick["twtt_surf"], rdata.dt)
  
    # tmp auto filtering handle of 2020 ak data
    if fpath.split("/")[-1].startswith("2020"):
        [b, a] = sp.signal.butter(N=5, Wn=1e6, btype="lowpass", fs=fs)
        pc_lp = sp.signal.filtfilt(b, a, rdata.dat, axis=0)
        rdata.proc_data = np.abs(pc_lp)

    return rdata

def read_mat(fpath):
# method to ingest .mat files. for older matlab files, sp.io works and h5py does not. for newer files, h5py works and sp.io does not 
    rdata = radar(fpath.split("/")[-1])
    try:
        f = h5py.File(fpath, "r")
        rdata.snum = int(f["block"]["num_sample"][0])[-1]
        rdata.tnum = int(f["block"]["num_trace"][0])[-1] 
        rdata.dt = float(f["block"]["dt"][0])
        rdata.clut = np.array(f["block"]["clutter"])

        rdata.navdat.df["lon"] = f["block"]["lon"].flatten()
        rdata.navdat.df["lat"] = f["block"]["lat"].flatten()
        rdata.navdat.df["elev"] = f["block"]["elev_air"].flatten()

        rdata.surf = utils.twtt2sample(f["block"]["twtt_surf"].flatten(), rdata.dt)
        rdata.dat = np.array(f["block"]["amp"])
        f.close()

    except:
        try:
            f = sp.io.loadmat(fpath)
            dt = float(f["block"]["dt"][0])
            num_trace = int(f["block"]["num_trace"][0])
            num_sample = int(f["block"]["num_sample"][0])
            dist = f["block"]["dist"][0][0].flatten()
            lon = f["block"]["lon"][0][0].flatten().astype(np.float64)
            lat = f["block"]["lat"][0][0].flatten().astype(np.float64)
            alt = f["block"]["elev_air"][0][0].flatten().astype(np.float64)
            twtt_surf = f["block"]["twtt_surf"][0][0].flatten().astype(np.float64)
            amp = f["block"]["amp"][0][0]
            clutter = f["block"]["clutter"][0][0]

        except Exception as err:
            print("ingest Error: " + str(err))
            pass

    print("----------------------------------------")
    print("Loading: " + fpath.split("/")[-1])
    
    # transpose amp and clutter if flipped
    if amp.shape[0] == num_trace and amp.shape[1] == num_sample:
        amp = np.transpose(amp)  
    if clutter.shape[0] == num_trace and clutter.shape[1] == num_sample:
        clutter = np.transpose(clutter)
    
    # replace twtt_surf with nan"s if no data
    if not np.any(twtt_surf):
        twtt_surf.fill(np.nan)

    # calculate surface elevation 
    elev_gnd = alt - twtt_surf*C/2
    
    # create dictionary to hold picks
    pick = {}
    pick["twtt_surf"] = twtt_surf

    # convert lon, lat, elev to navdat object of nav class
    wgs84_proj4 = "+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs"
    nav0 = nav.navpath()
    nav0.csys = wgs84_proj4
    nav0.navdat = np.column_stack((lon,lat,alt))

    # create dist array  - convert nav to meters then find cumulative euclidian distance
    ak_nad83_proj4 = "+proj=aea +lat_1=55 +lat_2=65 +lat_0=50 +lon_0=-154 +x_0=0 +y_0=0 +ellps=GRS80 +datum=NAD83 +units=m +no_defs" 
    nav0_xform = nav0.transform(ak_nad83_proj4)
    dist = utils.euclid_dist(nav0_xform)

    # interpolate nav data if not unique location for each trace
    if len(np.unique(lon)) < num_trace:
        nav0.navdat[:,0] = utils.interp_array(lon)
    if len(np.unique(lat)) < num_trace:
        nav0.navdat[:,1] = utils.interp_array(lat)
    if len(np.unique(dist)) < num_trace:
        dist = utils.interp_array(dist)

    trace = np.arange(num_trace)
    sample = np.arange(num_sample)

    # replace potential erroneous twtt_surf values with nan
    # get indices where twtt_surf is not nan
    idx = np.logical_not(np.isnan(twtt_surf))
    twtt_surf[np.where(twtt_surf[idx] > sample[-1]*dt)[0]] = np.nan
    twtt_surf[np.where(twtt_surf[idx] <= sample[1]*dt)[0]] = np.nan

    # get indices of twtt_surf
    surf_idx = np.rint(twtt_surf/dt)

    return {"dt": dt, "trace": trace, "sample": sample, "navdat": nav0, "elev_gnd": elev_gnd, "pick": pick, "surf_idx": surf_idx, "dist": dist, "amp": amp, "clutter": clutter} # other fields?
