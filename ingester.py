import h5py
import numpy as np

class ingester:
    # ingester is a class to create a data ingester
    # builds a dictionary with data and metadata from the file
    # ned to decide on a standard set of fields
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
        # read in HDF5 .mat radar block file
        f = h5py.File(fpath, 'r')

        # parse data
        amp = np.array(f['block']['amp'])
        amp = np.transpose(amp)  
        ch0 = np.array(f['block']['ch0'])
        dist = np.array(f['block']['dist'])
        elev = np.array(f['block']['elev_air'])
        dt = f['block']['dt'][()]
        # print(list(f['block']))

        if 'chirp' in list(f['block'].keys()):    
            bw = f['block']['chirp']['bw'][()]   
            cf = f['block']['chirp']['cf'][()]    
            pLen = f['block']['chirp']['len'][()]

        return {"amp": amp,"dist": dist,"dt": dt} # clutter? other fields?

