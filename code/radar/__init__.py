# RAGU - Radar Analysis Graphical Utility
#
# copyright © 2020 btobers <tobers.brandon@gmail.com>
#
# distributed under terms of the GNU GPL3.0 license
### imports ###
from radar.flags import flags
from radar.pick import pick
import numpy as np
import scipy.signal as signal

class radar(object):
    """
    the radar class holds the relevant information for a radar profile.
    keep track of processing steps with the flags attribute.
    """
    # import processing tools
    from radar.processing import get_tzero_samp, tzero_shift, tpowGain, lowpass, shiftSim, restore

    def __init__(self, fpath):
        # basic data file attributes
        #: str, file path
        self.fpath = fpath
        #: str, file name
        self.fn = None
        #: str, scientific data type
        self.dtype = None
        #: int, number of samples per trace
        self.snum = None
        #: int, the number of traces in the file
        self.tnum = None
        #: float, time between samples
        self.dt = None
        #: np.ndarray(snum x tnum) ingested radar data
        self.dat = None
        #: int, number of data channels
        self.nchan = None
        #: dict, signal info
        self.sig = {}
        #: radar flags object
        self.flags = flags()

        # per-trace attributes
        #: navdf consisting of [lon, lat, hgt, x, y, z, dist]
        self.navdf = None

        # sample-wise attributes
        #: np.ndarray(snum,) The two way travel time to each sample, in us
        self.twtt = None

        # optional attributes
        #: list, log of dataset operations history
        self.log = []
        #: np.ndarray(tnum,), surface elevation per trace
        self.srfElev = None
        #: np.ndarray(snum x tnum), processed radat data - this is what will actually be displayed, as to not modify original data
        self.proc = None
        #: np.ndarray(snum x tnum), clutter simulation stored in dB for viewing
        self.sim = None
        #: pick object
        self.pick = pick()
        #: pandas dataframe output data
        self.out = None

        return


    # set processed radar data method
    def set_proc(self, dat):
        # dB it
        self.proc = self.dBscale(dat)
        # generate pyramid arrays
        self.dPyramid = self.genPyramids(self.proc)

        return


    # set simter simulation data method
    def set_sim(self, dat):
        # dB it
        self.sim = self.dBscale(dat)
        # generate pyramid arrays
        self.sPyramid = self.genPyramids(self.sim)

        return


    # set ground height
    def set_srfElev(self, dat):
        #: np.ndarray(tnum,) data, surface elevation per trace
        self.srfElev = dat

        return


    # set output dataframe
    def set_out(self, dat):
        self.out = dat

        return


    # convert amplitude array to dB log scale
    def dBscale(self, dat):
        # convert to power
        pow = np.power(dat.astype(np.float), 2)
        # mask zero-power values
        pow[pow == 0] = np.nan
        # dB it
        dB = 10*np.log10(pow)

        return dB


    def genPyramids(self, dat):
        # downsample in fast time by 2^0, 2^1, 2^2, 2^3
        pyramid = []
        # add pyramid arrays to list
        if self.fpath.endswith("h5"):
            for i in range(4):
                pyramid.append(dat[::2**i,:])
        else:
            pyramid.append(dat)

        return pyramid