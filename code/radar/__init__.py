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
        self.proc_data = None
        #: np.ndarray(snum x tnum) clutter simulation
        self.clut = None
        #: pick object
        self.pick = pick()

        return

    def genPyramids(self):
        # Only downsample in fast time to make pick export easier
        self.dPyramid = []
        self.cPyramid = []

        for i in range(4):
            self.dPyramid.append(self.proc_data[::2**i,:])
            self.cPyramid.append(self.clut[::2**i,:])

        return

class pick(object):
    """
    pick class holds the relevant radar pick information.
    """
    def __init__(self):
        # necessary pick objects - pick dictionaries contain arrays of pick sample numbers at each trace in rdata
        self.existing = self.existing()
        self.current = self.current()
        return

    class existing(object):
        #: np.ndarray(tnum,) containing existing data file twtt to surface for a given trace
        twtt_surf = np.array(())
        #: dict, containing  existing data file twtt to subsurface pick segments/layers.
        # individual segments/layers are stored as arrays [np.ndarray(tnum,)] containing twtt in 
        # second to a picked reflection horizon, and NaN where no pick exists for a given trace.
        # twtt_subsurf[n] is 0-indexed, representing individual pick segments/layers
        twtt_subsurf = {}

    class current(object):
        #: np.ndarray(tnum,) containing current session surface pick in sample number 
        surf = np.array(())
        #: dict, containing  current data file subsurface pick segments/layers.
        # individual segments/layers are stored as arrays [np.ndarray(tnum,)] containing
        # the sample number of a picked reflection horizon, and NaN where no pick exists 
        # for a given trace. subsurf[n] is 0-indexed, representing individual pick segments/layers
        subsurf = {}
        #: np.ndarray(tnum,) containing current session optimized surface pick in sample number 
        surf_opt = np.array(())
        #: dict, containing  current data file optimized subsurface pick segments/layers.
        subsurf_opt = {}