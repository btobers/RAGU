# RAGU - Radar Analysis Graphical Utility
#
# copyright © 2020 btobers <tobers.brandon@gmail.com>
#
# distributed under terms of the GNU GPL3.0 license
### imports ###
from ragu.tools import utils
from ragu.radar.flags import flags
from ragu.radar.pick import pick
from ragu.radar.processing import proc
from ragu.raguError import raguError
import numpy as np
import scipy.signal as signal

class garlic(object):
    """
    garlic is the main dataset object for ragu - the supreme ingredient -
    containing all of the relevant information for each radar profile.
    keep track of processing steps with the flags attribute.
    """
    #: Attributes that every RadarData object should have.
    #: These should not be None.
    required_attrs = ["fpath",
                        "fn",
                        "dtype",
                        "nchan",
                        "dat",
                        "dt",
                        "snum",
                        "tnum",
                        "twtt",
                        "navdf",
                        "truncs"]
    # import processing tools
    from ragu.radar.processing import reverse, set_tzero, tzero_shift, flatten, vertical_roll, tpowGain, filter, hilbertxform, removeSlidingMeanFFT, restack, undo, redo, reset

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
        #: int, number of samples above row zero in data array that have been truncated across all traces
        self.truncs = 0
        #: float, antenna separation (meters) - if rx and tx gps exist then this will be converted to an array with per trace separation distance upon data ingest
        self.asep = 0
        #: dict, signal info
        self.info = {}
        #: np.ndarray(snum x tnum), raw ingested radar data
        self.dat = None
        #: radar data processing class object
        self.proc = proc()
        #: np.ndarray(snum x tnum), dB"d radar data pyramids
        self.dPyramid = None
        #: np.ndarray(snum x tnum), dB"d clutter simulation
        self.sim = None
        #: np.ndarray(snum x tnum), dB"s clutter simulation pyramids
        self.sPyramid = None
        #: radar flags object
        self.flags = flags()
        # geographic crs string
        self.geocrs = None
        # xyz crs string
        self.xyzcrs = None
        # bool: store data as power in decibels
        self.dbit = True

        # per-trace attributes
        #: navigation dataframe consisting of [lon, lat, hgt, x, y, z, dist], where each field is of type and size np.ndarray(tnum,)
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
        # set sim flag to True
        self.flags.sim = True
        return


    # set twtt array
    def set_twtt(self, arr = None):
        if arr is not None:
            self.twtt = arr
        else:
            if not [x for x in (self.snum, self.tnum) if x is None]:
                self.twtt = np.arange(self.snum) * self.dt
        return

    # get twtt array
    def get_twtt(self):
        return self.twtt


    # set ground height
    def set_srfElev(self, dat=None):
        #: np.ndarray(tnum,) data, surface elevation per trace
        if dat is not None:
            self.srfElev = dat
        else:
            # account for time zero shift, and truncation (mostly relevant for cresis data)
            self.srfElev = utils.srfpick2elev(self.pick.horizons[self.pick.get_srf()] + self.flags.sampzero + self.truncs,
                                            self.navdf["twtt_wind"].to_numpy(),
                                            self.navdf["elev"].to_numpy(), 
                                            self.dt,
                                            self.tnum,
                                            self.asep)
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
        if self.dbit:
            # convert to power
            pow = np.power(dat.astype(float), 2)
            # mask zero-power values
            pow[pow == 0] = np.nan
            # dB it
            out = 10*np.log10(pow)
        else:
            out = dat
        return out


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


    def check_attrs(self):
        """check if required garlic objects exist
        this format is modified from ImpDAR
        ------
        raguError
            If any required attribute is None,
            or any optional attribute is fully absent
        """
        # fn is required but defined separately
        for attr in self.required_attrs:
            if not hasattr(self, attr):
                raise raguError("{:s} is missing.".format(attr))
            if getattr(self, attr) is None:
                raise raguError("{:s} is None.".format(attr))
 
        # check data array shape
        if (self.dat.shape[:2] != (self.snum, self.tnum)):
            try:
                self.snum, self.tnum = self.get_dat().shape[:2]
            except:
                raise raguError("Data shape is inconsistent with the number of traces and the number of samples.\nData Array Shape: {}\nSamples: {}\nTraces: {}\nChannels: {}".format(self.dat.shape,self.snum,self.tnum,self.nchan))

        # check navdf
        for k in ["lon","lat","elev","dist"]:
            if k not in self.navdf:
                raise raguError("{:s} is missing from the nav dataframe.".format(k))

        if self.navdf.shape[0] != self.tnum:
            raise raguError("Nav dataframe shape is inconsistent with the number of traces.\nNav dataframe shape: {}\nTraces: {}".format(self.navdf.shape[0],self.tnum))

        return