import h5py
import numpy as np
from nav import *
import utils
import matplotlib.pyplot as plt
import scipy.io as scio
import sys

class ingester:
    # ingester is a class to create a data ingester
    # builds a dictionary with data and metadata from the file
    # need to decide on a standard set of fields
    def __init__(self, ftype):
        # ftype is a string specifying filetype
        # valid options -
        # h5py
        valid_types = ["h5py"] # can add more to this
        if (ftype not in valid_types):
            print("Invalid file type specifier")
            print("Valid file types:")
            print(valid_types)
            exit(1)

        self.ftype = ftype

    def read(self, fpath):
        # wrapper method for reading in a file
        # better ways to do this than an if/else
        # but for a few file types this is easier
        if(self.ftype == "h5py"):
            return self.h5py_read(fpath)
        else:
            print("File reader for format {} not built yet".format(self.ftype))
            exit(1)

    def h5py_read(self, fpath):
        # try reading HDF5 radar file
        try:
            f = h5py.File(fpath, "r")
            # print(list(f["block"]))

            # ingest for new 2019 data onward
            if fpath.endswith(".h5"):
                crs = f["loc0"].attrs["CRS"]
                dt = float(1/(f["rx0"].attrs["fsHz"]))
                num_trace = f["rx0"].attrs["numTraces"]
                num_sample = f["rx0"].attrs["samplesPerTrace"]
                lon =  np.array(f["loc0"]["lon"]).flatten().astype(np.float64)
                lat =  np.array(f["loc0"]["lat"]).flatten().astype(np.float64)
                elev_air =  np.array(f["loc0"]["altM"]).flatten().astype(np.float64)
                twtt_surf = np.zeros(num_trace)
                amp = np.array(f["proc0"])
                if "sim0" in f.keys():
                    clutter = np.array(f["sim0"])
                else:
                    clutter = np.ones(amp.shape)
                

            # ingest matlab hdf5 blocks
            else:
                dt = float(f["block"]["dt"][0])
                num_trace = int(f["block"]["num_trace"][0])
                num_sample = int(f["block"]["num_sample"][0])
                dist = np.array(f["block"]["dist"]).flatten()
                lon = np.array(f["block"]["lon"]).flatten()
                lat = np.array(f["block"]["lat"]).flatten()
                elev_air = np.array(f["block"]["elev_air"]).flatten()
                twtt_surf = np.array(f["block"]["twtt_surf"]).flatten()
                amp = np.array(f["block"]["amp"])
                clutter = np.array(f["block"]["clutter"])
                dist = dist / 10.   # divide distance by 10 to get out of pickGUI format

            f.close()

        # if h5py.File does not work, try scipy.io  
        except:
            # print("Ingest Error: File cannot be read with h5py, trying with scipy.io" )
            try:
                f = scio.loadmat(fpath)
                
                dt = float(f["block"]["dt"][0])
                num_trace = int(f["block"]["num_trace"][0])
                num_sample = int(f["block"]["num_sample"][0])
                dist = f["block"]["dist"][0][0].flatten()
                lon = f["block"]["lon"][0][0].flatten()
                lat = f["block"]["lat"][0][0].flatten()
                elev_air = f["block"]["elev_air"][0][0].flatten()
                twtt_surf = f["block"]["twtt_surf"][0][0].flatten()
                amp = f["block"]["amp"][0][0]
                clutter = f["block"]["clutter"][0][0]
                dist = dist / 10.   # divide distance by 10 to get out of pickGUI format

            except Exception as err:
                print("ingest Error: " + str(err))
                pass

        # transpose amp and clutter if flipped
        if amp.shape[0] == num_trace and amp.shape[1] == num_sample:
            amp = np.transpose(amp)  
        if clutter.shape[0] == num_trace and clutter.shape[1] == num_sample:
            clutter = np.transpose(clutter)

        # convert lon, lat, elev to navdat object of nav class
        wgs84_proj4 = "+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs"
        navdat = nav()
        navdat.csys = wgs84_proj4
        navdat.navdat = np.column_stack((lon,lat,elev_air))

        # create dist array if new .h5 data - convert nav to meters then find cumulative euclidian distance
        if fpath.endswith(".h5"):
            ak_nad83_proj4 = "+proj=aea +lat_1=55 +lat_2=65 +lat_0=50 +lon_0=-154 +x_0=0 +y_0=0 +ellps=GRS80 +datum=NAD83 +units=m +no_defs" 
            navdat_transform = navdat.transform(ak_nad83_proj4)
            dist = utils.euclid_dist(navdat_transform)

        # interpolate nav data if not unique location for each trace
        if len(np.unique(lon)) < num_trace:
            navdat.navdat[:,0] = utils.interp_array(lon)
            navdat.navdat[:,1] = utils.interp_array(lat)
            dist = utils.interp_array(dist)
        
        return {"dt": dt, "num_trace": num_trace, "num_sample": num_sample, "navdat": navdat, "twtt_surf": twtt_surf,"dist": dist, "amp": amp, "clutter": clutter} # other fields?