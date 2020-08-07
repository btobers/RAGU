# NOSEpick - Nearly Optimal Subsurface Extractor
#
# copyright © 2020 btobers <tobers.brandon@gmail.com>
#
# distributed under terms of the GNU GPL3.0 license.

import numpy as np

class radar(object):
    """
    the radar class holds the relevant information for a radar profile.
    keep track of processing steps with the flags attribute.
    """
    def __init__(self, fpath):
        # basic data file attributes
        #: str, file path
        self.fpath = fpath
        #: str, scientific data type
        self.dtype = None
        #: int, number of samples per trace
        self.snum = None
        #: int, the number of traces in the file
        self.tnum = None
        #: float, spacing between samples in travel time [seconds]
        self.dt = None
        #: np.ndarray(snum x tnum) ingested radar data
        self.dat = None
        #: int, channel number of the data
        self.chan = None

        # per-trace attributes
        #: navdf consisting of [lon, lat, elev, x, y, z, dist]
        self.navdf = None

        # sample-wise attributes
        #: np.ndarray(snum,) The two way travel time to each sample, in us
        self.twtt = None

        # optional attributes
        #: np.ndarray(tnum,) surface index per trace [samle #]
        self.surf = None
        #: np.ndarray(tnum,) ground elevation per trace [m.a.s.l.]
        self.elev_gnd = None
        #: np.ndarray(snum x tnum) processed radat data - this is what will actually be displayed, as to not modify original data
        self.proc = None
        #: np.ndarray(snum x tnum) clutter simulation stored in dB for viewing
        self.clut = None
        #: pick object
        self.pick = pick()

        return


    # set processed radar data method
    def set_proc(self, dat):
        # dB it
        dat = self.dBscale(dat)
        self.proc = dat

        return


    # convert amplitude array to dB log scale
    def dBscale(self, dat):
        pow = np.power(dat, 2)
        # dB it - ignore divide by zero warning for zero-power values
        with np.errstate(divide="ignore"):
            dB = np.log10(pow)
        # set -9999 as nodata value
        dB[~np.isfinite(dB)] = -9999

        return dB


    def genPyramids(self):
        # downsample in fast time by 2^0, 2^1, 2^2, 2^3
        self.dPyramid = []
        self.cPyramid = []

        for i in range(4):
            self.dPyramid.append(self.proc[::2**i,:])
            self.cPyramid.append(self.clut[::2**i,:])

        return


class pick(object):
    """
    pick class holds the relevant radar pick information.
    """
    def __init__(self):
        # necessary pick objects - existing and current

        #: np.ndarray(tnum,) containing existing data file twtt to surface for a given trace
        self.existing_twttSurf = np.array(())
        #: dict, containing  existing data file twtt to subsurface pick segments/layers.
        # individual segments/layers are stored as arrays [np.ndarray(tnum,)] containing twtt in 
        # second to a picked reflection horizon, and NaN where no pick exists for a given trace.
        # twtt_subsurf[n] is 0-indexed, representing individual pick segments/layers
        self.existing_twttSubsurf = {}

        #: np.ndarray(tnum,) containing current session surface pick in sample number 
        self.current_surf = np.array(())
        #: np.ndarray(tnum,) containing current session optimized surface pick in sample number 
        self.current_surfOpt = np.array(())
        #: dict, containing  current data file subsurface pick segments/layers.
        # individual segments/layers are stored as arrays [np.ndarray(tnum,)] containing
        # the sample number of a picked reflection horizon, and NaN where no pick exists 
        # for a given trace. subsurf[n] is 0-indexed, representing individual pick segments/layers
        self.current_subsurf = {}
        #: dict, containing  current data file optimized subsurface pick segments/layers.
        self.current_subsurfOpt = {}

        return