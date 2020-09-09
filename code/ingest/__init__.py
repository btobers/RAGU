# NOSEpick - Nearly Optimal Subsurface Extractor
#
# copyright © 2020 btobers <tobers.brandon@gmail.com>
#
# distributed under terms of the GNU GPL3.0 license.
"""
radar data ingest wrapper
"""
### imports ###
from ingest import ingest_oibAK, ingest_gssi, ingest_sharad, ingest_marsis
from tools import utils
import numpy as np

class ingest:
    # ingest is a class which builds a dictionary holding data and metadata from the file
    def __init__(self, ftype):
        # ftype is a string specifying filetype
        # valid options -
        # hdf5, mat, segy, img
        valid_types = ["h5", "mat", "dzt", "img"]
        if (ftype.lower() not in valid_types):
            print("Invalid file type specifier: " + ftype)
            print("Valid file types:")
            print(valid_types)
            exit(1)

        self.ftype = ftype.lower()


    def read(self, fpath, simpath, navcrs, body):
        # wrapper method for reading in a file
        # better ways to do this than an if/else
        # but for a few file types this is easier
        if (self.ftype == "h5"):
            self.rdata = ingest_oibAK.read_h5(fpath, navcrs, body)
        elif (self.ftype == "mat"):
            self.rdata = ingest_oibAK.read_mat(fpath, navcrs, body)
        elif (self.ftype == "dzt"):
            self.rdata = ingest_gssi.read(fpath, navcrs, body)
        elif (self.ftype == "img"):
            self.rdata = ingest_sharad.read(fpath, simpath, navcrs, body)
        # elif (self.ftype == "dat"):
        #     self.rdata = ingest_marsis.read(fpath, simpath, navcrs, body)

        else:
            print("File reader for format {} not built yet".format(self.ftype))
            exit(1)

        return self.rdata


    # import_picks is a method of the ingester class which loads in existing picks from a text file
    def import_picks(self, fpath):
        if fpath.endswith("csv"):
            dat = np.genfromtxt(fpath, delimiter=",", dtype = None, names = True)
            twtt_bed = dat["twtt_bed"]
            if len(twtt_bed) == self.rdata.tnum:
                # add to current subsurf dictionary as next segment
                count = len(self.rdata.pick.current_subsurf)
                self.rdata.pick.current_subsurf[str(count)] = utils.twtt2sample(twtt_bed, self.rdata.dt)

        return 