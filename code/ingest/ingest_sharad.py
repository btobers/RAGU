### IMPORTS ###
import numpy as np
from tools import nav, utils

# method to read PDS SHARAD USRDR data
def read(fpath):
    print("----------------------------------------")
    print("Loading: " + fpath.split("/")[-1])
    # convert binary .img PDS RGRAM to numpy array
    # reshape array with 3600 lines
    dtype = np.dtype("float32")     
    with open(fpath, "rb") as f:
        amp = np.fromfile(f, dtype)     
    l = len(amp)
    num_sample = 3600
    num_trace = int(len(amp)/num_sample)
    amp = amp.reshape(num_sample,num_trace)
    
    # convert binary .img clutter sim product to numpy array
    with open(fpath.replace("rgram","geom_combined"), "rb") as f:
        clutter = np.fromfile(f, dtype)   
    clutter = clutter.reshape(num_sample,num_trace)

    # open geom nav file for rgram
    geom_path = fpath.replace("rgram","geom").replace("img","tab")

    nav_file = np.genfromtxt(geom_path, delimiter = ",", dtype = str)

    # get necessary data from image file and geom
    dt = .0375e-6                                                                           # sampling interval for 3600 real-values voltage samples
    lon = nav_file[:,3].astype(np.float64)
    lat = nav_file[:,2].astype(np.float64)
    alt = nav_file[:,5].astype(np.float64) - nav_file[:,4].astype(np.float64)               # [km]

    elev_gnd = np.repeat(np.nan, num_trace)

    dist = np.arange(num_trace)

    twtt_surf = np.repeat(np.nan, num_trace)

    # create dictionary to hold picks
    pick = {}
    pick["twtt_surf"] = twtt_surf

    # create nav object to hold lon, lat, elev
    nav0 = nav.navpath()
    nav0.csys = "+proj=longlat +a=3396190 +b=3376200 +no_defs"
    nav0.navdat = np.column_stack((lon,lat,alt))

    # create dist array - convert nav to meters then find cumulative euclidian distance
    mars_equidistant_proj4 = "+proj=eqc +lat_ts=0 +lat_0=0 +lon_0=180 +x_0=0 +y_0=0 +a=3396190 +b=3396190 +units=m +no_defs" 
    nav0_xform = nav0.transform(mars_equidistant_proj4)
    dist = utils.euclid_dist(nav0_xform)

    trace = np.arange(num_trace)
    sample = np.arange(num_sample)


    # get indices of twtt_surf
    surf_idx = np.rint(twtt_surf/dt)
    return {"dt": dt, "trace": trace, "sample": sample, "navdat": nav0, "elev_gnd": elev_gnd, "pick": pick, "surf_idx": surf_idx, "dist": dist, "amp": amp, "clutter": clutter} # other fields?