### IMPORTS ###
import h5py
import numpy as np
from tools import nav, utils, processing

### method to ingest OIB-AK radar .h5 data format ###
def read(fpath):
    print("----------------------------------------")
    print("Loading: " + fpath.split("/")[-1])
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
    fs = f["raw"]["rx0/"].attrs["samplingFrequency-Hz"]        # sampling frequency, Hz
    num_trace = f["raw"]["rx0"].attrs["numTrace"]              # number of traces in rgram
    num_sample = f["raw"]["rx0"].attrs["samplesPerTrace"]      # samples per trace in rgram

    # initialize nav path
    nav0 = nav.navpath()
    # pull necessary ext group nav data - use more precise Larsen nav data pulled from Trimble if available
    if "nav0" in f["ext"].keys():
        lon = f["ext"]["nav0"]["lon"][:].astype(np.float64)
        lat = f["ext"]["nav0"]["lat"][:].astype(np.float64)
        alt = f["ext"]["nav0"]["altM"][:].astype(np.float64)
        crs = f["ext"]["nav0"].attrs["CRS"].decode("utf-8") 
    # pull raw loc0 nav data if Larsen nav DNE
    else:
        lon = f["raw"]["loc0"]["lon"][:].astype(np.float64)
        lat = f["raw"]["loc0"]["lat"][:].astype(np.float64)
        alt = f["raw"]["loc0"]["altM"][:].astype(np.float64)
        crs = f["raw"]["loc0"].attrs["CRS"].decode("utf-8")        
    
    # pull lidar surface elevation if possible
    if "srf0" in f["ext"].keys():
        elev_gnd = f["ext"]["srf0"][:]                          # surface elevation from lidar, averaged over radar first fresnel zone per trace (see code within /zippy/MARS/code/xped/hfProc/ext)
    # create empty arrays to hold surface elevation and twtt otherwise
    else:
        elev_gnd = np.repeat(np.nan, num_trace)

    # pull necessary drv group data
    pc = f["drv/proc0"][:]                                      # pulse compressed array
    amp = np.abs(pc)

    if "clutter0" in f["drv"].keys():
        clutter = f["drv"]["clutter0"][:]                       # simulated clutter array
    else:
        clutter = np.ones(amp.shape)                            # empty clutter array if no sim exists
    
    # read in any existing picks
    pick = {}
    if "twtt_surf" in f["drv"]["pick"].keys():
        pick["twtt_surf"] = f["drv"]["pick"]["twtt_surf"][:]
    else:
        pick["twtt_surf"] = np.repeat(np.nan, num_trace)

    #  determine how many subsurface pick layers exist in the file - read each in as a numpy array to the pick dictionary
    num_file_pick_lyr = len(fnmatch.filter(f["drv"]["pick"].keys(), "twtt_subsurf*"))
    if num_file_pick_lyr > 0:
        # iterate through any existing subsurface pick layers to import
        for _i in range(num_file_pick_lyr):
            pick["twtt_subsurf" + str(_i)] = np.array(f["drv"]["pick"]["twtt_subsurf" + str(_i)])

    f.close()                                                   # close the file

    # create dist array  - convert nav to meters then find cumulative euclidian distance
    nav0.navdat = np.column_stack((lon,lat,alt))
    if "wgs" in crs.lower(): 
        nav0_proj4 = "+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs"
    else:
        print("Unknown nav coordinate reference system")
        sys.exit()    
    nav0.csys = nav0_proj4
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

    dt = 1/fs
    trace = np.arange(num_trace)
    sample = np.arange(num_sample)

    # replace potential erroneous twtt_surf values with nan
    # get indices where twtt_surf is not nan
    idx = np.logical_not(np.isnan(pick["twtt_surf"]))
    pick["twtt_surf"][np.where(pick["twtt_surf"][idx] > sample[-1]*dt)[0]] = np.nan
    pick["twtt_surf"][np.where(pick["twtt_surf"][idx] <= sample[1]*dt)[0]] = np.nan
    
    # get indices of twtt_surf
    surf_idx = utils.twtt2sample(pick["twtt_surf"], dt)

    # determine if non-unique navdat
    if np.all(nav0.navdat[:,0]==nav0.navdat[0,0]):
        print("h5py_read error: non-unique nav data")
        # set dist array to range from 0 to 1
        dist = np.linspace(0,1,num_trace)
    
    # tmp auto filtering handle of 2020 ak data
    if fpath.split("/")[-1].startswith("2020"):
        [b, a] = sp.signal.butter(N=5, Wn=1e6, btype="lowpass", fs=fs)
        pc = sp.signal.filtfilt(b, a, pc, axis=0)
        amp = np.abs(pc)

    return {"dt": dt, "trace": trace, "sample": sample, "navdat": nav0, "elev_gnd": elev_gnd, "pick": pick, "surf_idx": surf_idx, "dist": dist, "pc": pc, "amp": amp, "clutter": clutter, "num_file_pick_lyr": num_file_pick_lyr} # other fields?