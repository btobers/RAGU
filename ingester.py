import h5py
import numpy as np
from nav import *
import utils
import matplotlib.pyplot as plt
import scipy.io as scio
import sys,os
# from segpy.reader import create_reader


class ingester:
    # ingester is a class to create a data ingester
    # builds a dictionary with data and metadata from the file
    # need to decide on a standard set of fields
    def __init__(self, ftype):
        # ftype is a string specifying filetype
        # valid options -
        # hdf5, mat, segy
        valid_types = ["h5", "mat", "sgy", "img"] # can add more to this
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
        elif (self.ftype == "img"):
            return self.sharad_read(fpath)
        else:
            print("File reader for format {} not built yet".format(self.ftype))
            exit(1)


    def h5py_read(self, fpath):
        # method to ingest OIB-AK radar .h5 data format - all data should soon be in this format
        print('----------------------------------------')
        print("Loading: " + fpath.split("/")[-1])
        f = h5py.File(fpath, "r")                               # read in .h5 file

        # pull necessary raw group data
        fs = f["raw/rx0/"].attrs["samplingFrequency-Hz"]        # sampling frequency, Hz
        num_trace = f["raw/rx0"].attrs["numTrace"]              # number of traces in rgram
        num_sample = f["raw/rx0"].attrs["samplesPerTrace"]      # samples per trace in rgram

        if "nav0" in f["ext"].keys():
            # pull necessary ext group data - use more precise Larsen nav data pulled from Trimble
            lon =  np.array(f["ext/nav0"]["lon"]).astype(np.float64)
            lat =  np.array(f["ext/nav0"]["lat"]).astype(np.float64)
            elev_air =  np.array(f["ext/nav0"]["altM"]).astype(np.float64)
            crs = f["ext/nav0"].attrs["CRS"].decode("utf-8") 
        else:
            # pull raw loc0 nav data
            lon =  np.array(f["raw/loc0"]["lon"]).astype(np.float64)
            lat =  np.array(f["raw/loc0"]["lat"]).astype(np.float64)
            elev_air =  np.array(f["raw/loc0"]["altM"]).astype(np.float64)
            crs = f["raw/loc0"].attrs["CRS"].decode("utf-8")             

        if "srf0" in f["ext"].keys():
            elev_surf = np.array(f["ext/srf0"])                # surface elevation from lidar, averaged over radar first fresnel zone per trace (see code within /zippy/MARS/code/xped/hfProc/ext)
            twtt_surf = np.array(f["drv/pick"]["twtt_surf"])
        else:
            elev_surf = np.repeat(np.nan, num_trace)
            twtt_surf = np.repeat(np.nan, num_trace)

        # pull necessary drv group data
        amp = np.abs(np.array(f["drv/proc0"]))                  # pulse compressed amplitude array
        if "clutter0" in f["drv"].keys():
            clutter = np.array(f["drv/clutter0"])               # simulated clutter array
        else:
            clutter = np.ones(amp.shape)

        f.close()

        # convert lon, lat, elev to nav object of nav class
        if "wgs" in crs.lower(): 
            nav0_proj4 = "+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs"
        else:
            print("Unknown nav coordinate reference system")
            sys.exit()
            
        nav0 = nav()
        nav0.csys = nav0_proj4
        nav0.navdat = np.column_stack((lon,lat,elev_air))

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

        dt = 1/fs

        trace = np.arange(num_trace)
        sample = np.arange(num_sample)
        # create sample time array 
        sample_time = np.arange(num_sample)*dt

        # replace potential erroneous twtt_surf values with nan
        # get indices where twtt_surf is not nan
        idx = np.logical_not(np.isnan(twtt_surf))
        twtt_surf[np.where(twtt_surf[idx] > sample_time[-1])[0]] = np.nan
        twtt_surf[np.where(twtt_surf[idx] <= sample_time[1])[0]] = np.nan
        
        # get indices of twtt_surf
        surf_idx = np.rint(twtt_surf/dt)

        return {"dt": dt, "num_trace": num_trace, "trace": trace, "num_sample": num_sample, "sample": sample, "sample_time": sample_time, "navdat": nav0, "elev_surf": elev_surf, "twtt_surf": twtt_surf, "surf_idx": surf_idx, "dist": dist, "amp": amp, "clutter": clutter} # other fields?


    def mat_read(self,fpath):
        # method to ingest .mat files. for older matlab files, scio works and h5py does not. for newer files, h5py works and scio does not 
        c = 299792458               # Speed of light at STP
        try:
            f = h5py.File(fpath, "r")
            dt = float(f["block"]["dt"][0])
            num_trace = int(f["block"]["num_trace"][0])
            num_sample = int(f["block"]["num_sample"][0])
            lon = np.array(f["block"]["lon"]).flatten().astype(np.float64)
            lat = np.array(f["block"]["lat"]).flatten().astype(np.float64)
            elev_air = np.array(f["block"]["elev_air"]).flatten().astype(np.float64)
            twtt_surf = np.array(f["block"]["twtt_surf"]).flatten().astype(np.float64)
            amp = np.array(f["block"]["amp"])
            clutter = np.array(f["block"]["clutter"])
            f.close()

        except:
            try:
                f = scio.loadmat(fpath)
                dt = float(f["block"]["dt"][0])
                num_trace = int(f["block"]["num_trace"][0])
                num_sample = int(f["block"]["num_sample"][0])
                dist = f["block"]["dist"][0][0].flatten()
                lon = f["block"]["lon"][0][0].flatten().astype(np.float64)
                lat = f["block"]["lat"][0][0].flatten().astype(np.float64)
                elev_air = f["block"]["elev_air"][0][0].flatten().astype(np.float64)
                twtt_surf = f["block"]["twtt_surf"][0][0].flatten().astype(np.float64)
                amp = f["block"]["amp"][0][0]
                clutter = f["block"]["clutter"][0][0]

            except Exception as err:
                print("ingest Error: " + str(err))
                pass

        print('----------------------------------------')
        print("Loading: " + fpath.split("/")[-1])
        
        # transpose amp and clutter if flipped
        if amp.shape[0] == num_trace and amp.shape[1] == num_sample:
            amp = np.transpose(amp)  
        if clutter.shape[0] == num_trace and clutter.shape[1] == num_sample:
            clutter = np.transpose(clutter)
        
        # replace twtt_surf with nan's if no data
        if not np.any(twtt_surf):
            twtt_surf.fill(np.nan)

        # calculate surface elevation 
        elev_surf = elev_air - twtt_surf*c/2
        
        # convert lon, lat, elev to navdat object of nav class
        wgs84_proj4 = "+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs"
        nav0 = nav()
        nav0.csys = wgs84_proj4
        nav0.navdat = np.column_stack((lon,lat,elev_air))

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
        # create sample time array 
        sample_time = np.arange(num_sample)*dt

        # replace potential erroneous twtt_surf values with nan
        # get indices where twtt_surf is not nan
        idx = np.logical_not(np.isnan(twtt_surf))
        twtt_surf[np.where(twtt_surf[idx] > sample_time[-1])[0]] = np.nan
        twtt_surf[np.where(twtt_surf[idx] <= sample_time[1])[0]] = np.nan

        # get indices of twtt_surf
        surf_idx = np.rint(twtt_surf/dt)

        return {"dt": dt, "num_trace": num_trace, "trace": trace, "num_sample": num_sample, "sample": sample, "sample_time": sample_time, "navdat": nav0, "elev_surf": elev_surf, "twtt_surf": twtt_surf, "surf_idx": surf_idx, "dist": dist, "amp": amp, "clutter": clutter} # other fields?


    def segypy_read(self, fpath):
        # method to ingest .sgy data
        # with open(fpath, 'rb') as segy_in_file:
        #     # The seg_y_dataset is a lazy-reader, so keep the file open throughout.
        #     seg_y_dataset = create_reader(segy_in_file, endian='>')  # Non-standard Rev 1 little-endian
        #     print(seg_y_dataset.num_traces())
        sys.exit()


    def sharad_read(self, fpath):
        # convert binary .img PDS RGRAM to numpy array
        # reshape array with 3600 lines
        fname = fpath.split("/")[-1]
        dtype = np.dtype('float32')     
        rgram = open(fpath, 'rb') 
        amp = np.fromfile(rgram, dtype)     
        l = len(amp)
        num_sample = 3600
        num_trace = int(len(amp)/num_sample)
        amp = amp.reshape(num_sample,num_trace)

        # open geom nav file for rgram
        geom_path = fpath.replace("rgram","geom").replace("img","tab")

        nav_file = np.genfromtxt(geom_path, delimiter = ',', dtype = str)

        # get necessary data from image file and geom
        dt = .0375e-6                                                       # sampling interval for 3600 real-values voltage samples
        lon = nav_file[:,3].astype(np.float64)
        lat = nav_file[:,2].astype(np.float64)
        elev_air = nav_file[:,5].astype(np.float64) - nav_file[:,4].astype(np.float64)       # [km]

        elev_surf = np.repeat(np.nan, num_trace)

        dist = np.arange(num_trace)

        twtt_surf = np.repeat(np.nan, num_trace)

        # create nav object to hold lon, lat, elev
        nav0 = nav()
        nav0.csys = "+proj=longlat +a=3396190 +b=3376200 +no_defs"
        nav0.navdat = np.column_stack((lon,lat,elev_air))

        # create dist array - convert nav to meters then find cumulative euclidian distance
        mars_equidistant_proj4 = "+proj=eqc +lat_ts=0 +lat_0=0 +lon_0=180 +x_0=0 +y_0=0 +a=3396190 +b=3396190 +units=m +no_defs" 
        nav0_xform = nav0.transform(mars_equidistant_proj4)
        dist = utils.euclid_dist(nav0_xform)

        clutter = np.ones(amp.shape)

        trace = np.arange(num_trace)
        sample = np.arange(num_sample)
        # create sample time array 
        sample_time = np.arange(num_sample)*dt

        # get indices of twtt_surf
        surf_idx = np.rint(twtt_surf/dt)
        return {"dt": dt, "num_trace": num_trace, "trace": trace, "num_sample": num_sample, "sample": sample, "sample_time": sample_time, "navdat": nav0, "elev_surf": elev_surf, "twtt_surf": twtt_surf, "surf_idx": surf_idx, "dist": dist, "amp": amp, "clutter": clutter} # other fields?