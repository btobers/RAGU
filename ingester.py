import h5py
import numpy as np

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
            f = h5py.File(fpath, 'r')
        
            # parse data
            # print(list(f['block']))
            dt = f['block']['dt'][()]
            num_trace = int(f['block']['num_trace'][0])
            num_sample = int(f['block']['num_sample'][0])
            dist = np.array(f['block']['dist'])
            lat = np.array(f['block']['lat'])
            lon = np.array(f['block']['lon'])
            elev = np.array(f['block']['elev_air'])
            amp = np.array(f['block']['amp'])
            if amp.shape[0] == num_trace and amp.shape[1] == num_sample:
                amp = np.transpose(amp)  
            clutter = np.array(f['block']['clutter'])
            if clutter.shape[0] == num_trace and clutter.shape[1] == num_sample:
                clutter = np.transpose(clutter)

            if 'chirp' in list(f['block'].keys()):    
                bw = f['block']['chirp']['bw'][()]   
                cf = f['block']['chirp']['cf'][()]    
                pLen = f['block']['chirp']['len'][()]

            return {"dt": dt, "dist": dist, "lat": lat, "lon": lon, "elev": elev, "amp": amp, "clutter": clutter} # other fields?

        except Exception as err:
            print(err)





