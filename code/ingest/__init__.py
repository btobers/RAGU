# RAGU - Radar Analysis Graphical Utility
#
# copyright © 2020 btobers <tobers.brandon@gmail.com>
#
# distributed under terms of the GNU GPL3.0 license
"""
radar data ingest wrapper
"""
### imports ###
from ingest import ingest_oibAK, ingest_pulseekko, ingest_gssi, ingest_sharad, ingest_marsis, ingest_lrs, ingest_cresis_rds, ingest_cresis_snow
from tools import utils
import numpy as np
import pandas as pd
import fnmatch

class ingest:
    # ingest is a class which builds a dictionary holding data and metadata from the file
    def __init__(self, fpath):
        # ftype is a string specifying filetype
        # valid options -
        # hdf5, mat, segy, img, dat, dt1, dzt, lbl
        valid_types = ["h5", "mat", "img", "dat", "dt1", "dzt", "gpz", "lbl" ]
        ftype = fpath.split(".")[-1].lower()
        
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
            try:
                self.rdata = ingest_cresis_snow.read_mat(self.fpath, navcrs, body)
            except:
                try:
                    self.rdata = ingest_cresis_rds.read_mat(self.fpath, navcrs, body)
                except:
                    self.rdata = ingest_oibAK.read_mat(self.fpath, navcrs, body)
        elif (self.ftype == "lbl"):
            self.rdata = ingest_lrs.read(self.fpath, simpath, navcrs, body)
        elif (self.ftype == "img"):
            self.rdata = ingest_sharad.read(self.fpath, simpath, navcrs, body)
        elif (self.ftype == "dat"):
            self.rdata = ingest_marsis.read(self.fpath, simpath, navcrs, body)
        elif (self.ftype == "dt1"):
            self.rdata = ingest_pulseekko.read_dt1(self.fpath, navcrs, body)
        elif (self.ftype == "gpz"):
            raise ValueError("Error: \tPulseEKKO GPZ project file ingester currently in development.\n\tExport lineset from EKKO_Project to read DT1 files with RAGU")
            # self.rdata = ingest_pulseekko.partition_project_file(self.fpath, navcrs, body)
        elif (self.ftype == "dzt"):
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
            if dat.shape[0] != self.rdata.tnum:
                raise ValueError("import_pick error:\t pick file size does not match radar data")
                return
            horizons = []
            keys = fnmatch.filter(dat.keys(), "*sample*")
            if len(keys) >= 1:
                for horizon in keys:
                    horizon = horizon.split("_")[0]
                    sample = dat[horizon + "_sample"].to_numpy()
                    if horizon in self.rdata.pick.horizons.keys():
                        if utils.nan_array_equal(self.rdata.pick.horizons[horizon], sample):
                            continue
                        else:
                            horizon = horizon + "_imported"
                    self.rdata.pick.horizons[horizon] = sample
                    horizons.append(horizon)

        return  horizons