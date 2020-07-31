# NOSEpick - Nearly Optimal Subsurface Extractor
#
# Copyright © 2020 btobers <tobers.brandon@gmail.com>
#
# Distributed under terms of the GNU GPL3.0 license.
"""
radar data ingest wrapper
"""
### imports ###
from ingest import ingest_oibAK, ingest_gssi, ingest_pulseekko, ingest_sharad

class ingest:
    # ingest is a class which builds a dictionary holding data and metadata from the file
    def __init__(self, ftype):
        # ftype is a string specifying filetype
        # valid options -
        # hdf5, mat, segy
        valid_types = ["h5", "mat", "sgy", "dzt", "img"] # can add more to this
        if (ftype.lower() not in valid_types):
            print("Invalid file type specifier: " + ftype)
            print("Valid file types:")
            print(valid_types)
            exit(1)

        self.ftype = ftype.lower()


    def read(self, fpath, navcrs, body):
        # wrapper method for reading in a file
        # better ways to do this than an if/else
        # but for a few file types this is easier
        if (self.ftype == "h5"):
            return ingest_oibAK.read_h5(fpath, navcrs, body)
        elif (self.ftype == "mat"):
            return ingest_oibAK.read_mat(fpath, navcrs, body)
        elif (self.ftype == "sgy"):
            return ingest_segy(fpath, navcrs, body)
        elif (self.ftype == "dzt"):
            return ingest_gssi.read(fpath, navcrs, body)
        elif (self.ftype == "img"):
            return ingest_sharad.read(fpath, navcrs, body)
        else:
            print("File reader for format {} not built yet".format(self.ftype))
            exit(1)