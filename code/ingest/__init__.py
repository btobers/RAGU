# RAGU - Radar Analysis Graphical Utility
#
# copyright © 2020 btobers <tobers.brandon@gmail.com>
#
# distributed under terms of the GNU GPL3.0 license
"""
radar data ingest wrapper
"""
### imports ###
from ingest import ingest_oibAK, ingest_pulseekko, ingest_gssi, ingest_sharad, ingest_marsis
from tools import utils
import numpy as np
import pandas as pd

class ingest:
    # ingest is a class which builds a dictionary holding data and metadata from the file
    def __init__(self, fpath):
        # ftype is a string specifying filetype
        ftype = fpath.split(".")[-1]
        valid_types = ["h5", "mat", "img", "dat", "DT1", "DZT" ]
        if (ftype not in valid_types):

            raise ValueError("Invalid file type specifier: " + 
                ftype + "\nValid file types: " + str(valid_types))

        self.fpath = fpath
        self.ftype = ftype


    def read(self, simpath, navcrs, body):
        # wrapper method for reading in a file
        # better ways to do this than an if/else
        # but for a few file types this is easier
        if (self.ftype == "h5"):
            self.rdata = ingest_oibAK.read_h5(self.fpath, navcrs, body)
        elif (self.ftype == "mat"):
            self.rdata = ingest_oibAK.read_mat(self.fpath, navcrs, body)
        elif (self.ftype == "img"):
            self.rdata = ingest_sharad.read(self.fpath, simpath, navcrs, body)
        elif (self.ftype == "dat"):
            self.rdata = ingest_marsis.read(self.fpath, simpath, navcrs, body)
        elif (self.ftype == "DT1"):
            self.rdata = ingest_pulseekko.read(self.fpath, navcrs, body)
        elif (self.ftype == "DZT"):
            self.rdata = ingest_gssi.read(self.fpath, navcrs, body)
        else:
            print("File reader for format {} not built yet".format(self.ftype))
            exit(1)

        # add ingest commands to log
        self.rdata.log('self.igst = ingest("{}")'.format(self.fpath))
        self.rdata.log('self.rdata = igst.read("{}","{}","{}")'.format(simpath,navcrs,body))

        return self.rdata


    # import_pick is a method of the ingester class which loads in existing picks from a text file
    def import_pick(self, fpath):
        if fpath.endswith("csv"):
            dat = pd.read_csv(fpath)
            horizon = "bed"
            sample = dat[horizon + "_sample"]
            if len(sample) == self.rdata.tnum:
                if horizon not in self.rdata.pick.horizons.keys():
                    self.rdata.pick.horizons[horizon] = sample
                else:
                    horizon = "bed_imported"
                    self.rdata.pick.horizons["bed_imported"] = sample
        return  horizon