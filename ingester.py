import h5py
import numpy as np
from nav import *
import utils
import matplotlib.pyplot as plt
import scipy.io as scio
import sys
# from segpy.reader import create_reader


class ingester:
    # ingester is a class to create a data ingester
    # builds a dictionary with data and metadata from the file
    # need to decide on a standard set of fields
    def __init__(self, ftype):
        # ftype is a string specifying filetype
        # valid options -
        # hdf5, mat, segy
        valid_types = ["h5", "mat", "sgy"] # can add more to this
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
        if (self.ftype == "h5"):
            return self.h5py_read(fpath)
        elif (self.ftype == "mat"):
            return self.mat_read(fpath)
        elif (self.ftype == "sgy"):
            return self.segypy_read(fpath)
        else:
            print("File reader for format {} not built yet".format(self.ftype))
            exit(1)

    def h5py_read(self, fpath):
        # method to ingest 2019+ data exported as .h5 files
        f = h5py.File(fpath, "r")
        crs = f["loc0"].attrs["CRS"]
        dt = float(1/(f["rx0"].attrs["fsHz"]))
        num_trace = f["rx0"].attrs["numTraces"]
        num_sample = f["rx0"].attrs["samplesPerTrace"]
        lon =  np.array(f["loc0"]["lon"]).flatten().astype(np.float64)
        lat =  np.array(f["loc0"]["lat"]).flatten().astype(np.float64)
        elev_air =  np.array(f["loc0"]["altM"]).flatten().astype(np.float64)
        twtt_surf = np.zeros(num_trace)         # needs to be updated once .las surface added to data files
        amp = np.array(f["proc0"])
        if "clutter0" in f.keys():
            clutter = np.array(f["clutter0"])
        else:
            clutter = np.ones(amp.shape)
        f.close()

        # replace twtt_surf with nan's if no data
        if not np.any(twtt_surf):
            twtt_surf.fill(np.nan)

        # convert lon, lat, elev to navdat object of nav class
        wgs84_proj4 = "+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs"
        navdat = nav()
        navdat.csys = wgs84_proj4
        navdat.navdat = np.column_stack((lon,lat,elev_air))

        # create dist array if new .h5 data - convert nav to meters then find cumulative euclidian distance
        ak_nad83_proj4 = "+proj=aea +lat_1=55 +lat_2=65 +lat_0=50 +lon_0=-154 +x_0=0 +y_0=0 +ellps=GRS80 +datum=NAD83 +units=m +no_defs" 
        navdat_transform = navdat.transform(ak_nad83_proj4)
        dist = utils.euclid_dist(navdat_transform)

        # interpolate nav data if not unique location for each trace
        if len(np.unique(lon)) < num_trace:
            navdat.navdat[:,0] = utils.interp_array(lon)
            navdat.navdat[:,1] = utils.interp_array(lat)
            dist = utils.interp_array(dist)
        
        return {"dt": dt, "num_trace": num_trace, "num_sample": num_sample, "navdat": navdat, "twtt_surf": twtt_surf,"dist": dist, "amp": amp, "clutter": clutter} # other fields?

    def mat_read(self,fpath):
        # method to ingest .mat files. for older matlab files, scio works and h5py does not. for newer files, h5py works and scio does not 
        try:
            f = h5py.File(fpath, "r")

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
            f.close()
            if dist[2] - dist[1] > 1e-2:
                dist = dist / 10.   # divide distance by 10 to get out of pickGUI format

        except:
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
                if dist[2] - dist[1] > 1e-2:
                    dist = dist / 10.   # divide distance by 10 to get out of pickGUI format

            except Exception as err:
                print("ingest Error: " + str(err))
                pass

        # transpose amp and clutter if flipped
        if amp.shape[0] == num_trace and amp.shape[1] == num_sample:
            amp = np.transpose(amp)  
        if clutter.shape[0] == num_trace and clutter.shape[1] == num_sample:
            clutter = np.transpose(clutter)

        # replace twtt_surf with nan's if no data
        if not np.any(twtt_surf):
            twtt_surf.fill(np.nan)

        # convert lon, lat, elev to navdat object of nav class
        wgs84_proj4 = "+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs"
        navdat = nav()
        navdat.csys = wgs84_proj4
        navdat.navdat = np.column_stack((lon,lat,elev_air))

        # interpolate nav data if not unique location for each trace
        if len(np.unique(lon)) < num_trace:
            navdat.navdat[:,0] = utils.interp_array(lon)
        if len(np.unique(lat)) < num_trace:
            navdat.navdat[:,1] = utils.interp_array(lat)
        if len(np.unique(dist)) < num_trace:
            dist = utils.interp_array(dist)
      
        return {"dt": dt, "num_trace": num_trace, "num_sample": num_sample, "navdat": navdat, "twtt_surf": twtt_surf,"dist": dist, "amp": amp, "clutter": clutter} # other fields?

    def segypy_read(self, fpath):
        # method to ingest .sgy data
        # with open(fpath, 'rb') as segy_in_file:
        #     # The seg_y_dataset is a lazy-reader, so keep the file open throughout.
        #     seg_y_dataset = create_reader(segy_in_file, endian='>')  # Non-standard Rev 1 little-endian
        #     print(seg_y_dataset.num_traces())
        sys.exit()