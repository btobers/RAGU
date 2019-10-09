import h5py
import numpy as np
from nav import *
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
        try:
        # read in HDF5 .mat radar block file
            f = h5py.File(fpath, "r")
            # print(list(f["block"]))


            # ingest for new 2019 data onward
            if fpath.endswith(".h5"):
                dt = float(1/(f["rx0"].attrs["fsHz"]))
                num_trace = f["rx0"].attrs["numTraces"]
                num_sample = f["rx0"].attrs["samplesPerTrace"]
                lon =  f["loc0"]["lon"]
                lat =  f["loc0"]["lat"]
                elev_air =  f["loc0"]["altM"]
                twtt_surf = np.zeros(num_trace) 
                # print('here')
                # sys.exit()
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


            # if "chirp" in list(f["block"].keys()):    
            #     bw = f["block"]["chirp"]["bw"][()]   
            #     cf = f["block"]["chirp"]["cf"][()]    
            #     pLen = f["block"]["chirp"]["len"][()]

            f.close()
            


        except Exception as err:
            print("Ingest Error: " + str(err) + "\nError using h5py - tying with scipy.io")
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


            except Exception as err:
                print(err)
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
        
        return {"dt": dt, "num_trace": num_trace, "num_sample": num_sample, "navdat": navdat, "twtt_surf": twtt_surf, "amp": amp, "clutter": clutter} # other fields?