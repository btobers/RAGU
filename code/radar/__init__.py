# RAGU - Radar Analysis Graphical Utility
#
# copyright © 2020 btobers <tobers.brandon@gmail.com>
#
# distributed under terms of the GNU GPL3.0 license
### imports ###
from tools import utils
from radar.flags import flags
from radar.pick import pick
from radar.processing import proc
import numpy as np
import scipy.signal as signal

class garlic(object):
    """
    garlic is the main dataset object for ragu - the supreme ingredient -
    containing all of the relevant information for each radar profile.
    keep track of processing steps with the flags attribute.
    """
    # import processing tools
    from radar.processing import set_tzero, tzero_shift, vertical_roll, tpowGain, filter, hilbertxform, undo, redo, reset

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
        #: float, sampling frequency
        self.fs = None
        #: float, pulse repition frequency
        self.prf = None
        #: int, number of data channels
        self.nchan = None
        #: dict, signal info
        self.info = {}
        #: np.ndarray(snum x tnum), raw ingested radar data
        self.dat = None
        #: np.ndarray(snum x tnum), processed radar data class object
        self.proc = proc()
        #: np.ndarray(snum x tnum), dB'd radar data pyramids
        self.dPyramid = None
        #: np.ndarray(snum x tnum), dB'd clutter simulation
        self.sim = None
        #: np.ndarray(snum x tnum), dB's clutter simulation pyramids
        self.sPyramid = None
        #: radar flags object
        self.flags = flags()

        # per-trace attributes
        #: navdf consisting of [lon, lat, hgt, x, y, z, dist]
        self.navdf = None

        # sample-wise attributes
        #: np.ndarray(snum,) The two way travel time to each sample, in us
        self.twtt = None

        # optional attributes
        #: list, history of dataset operations history - may be exported as script
        self.hist = []
        #: np.ndarray(tnum,), surface elevation per trace
        self.srfElev = None
        #: pick object
        self.pick = pick()
        #: pandas dataframe output data
        self.out = None

        return


    # set radar data
    def set_dat(self,dat):
        self.dat = dat


    # get radar data
    def get_dat(self):
        return self.dat


    # set processed radar data method
    def set_proc(self, dat):
        self.proc.set_curr_amp(dat)
        # dB it
        self.proc.set_curr_dB(self.dBscale(self.proc.curr_amp))
        # generate pyramid arrays
        self.dPyramid = self.genPyramids(self.proc.get_curr_dB())

        return


    # set simter simulation data method
    def set_sim(self, dat):
        # dB it
        self.sim = self.dBscale(dat)
        # generate pyramid arrays
        self.sPyramid = self.genPyramids(self.sim)

        return


    # set ground height
    def set_srfElev(self, dat=None):
        #: np.ndarray(tnum,) data, surface elevation per trace
        if dat is not None:
            self.srfElev = dat
        else:
            self.srfElev = utils.srfpick2elev(self.pick.horizons[self.pick.get_srf()],
                                            self.navdf["twtt_wind"].to_numpy(),
                                            self.navdf["elev"].to_numpy(), 
                                            self.dt,
                                            self.tnum)

        return


    # get ground height
    def get_srfElev(self):
        return self.srfElev


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
        if (self.dtype == "oibak") or (self.dtype == "cresis_snow") or (self.dtype == "cresis_rds"):
            for i in range(4):
                pyramid.append(dat[::2**i,:])
        else:
            pyramid.append(dat)

        return pyramid


    # append previous command to log
    def log(self, cmd=None):
        if cmd and isinstance(cmd,str):
            self.hist.append(cmd)