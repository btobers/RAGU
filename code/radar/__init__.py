# NOSEpick - Nearly Optimal Subsurface Extractor
#
# dopyright © 2020 btobers <tobers.brandon@gmail.com>
#
# distributed under terms of the GNU GPL3.0 license.
"""
radar data object wrapper, structure based on ImpDAR
"""
### imports ###
import numpy as np
# from scipy.io import loadmat
# from ..RadarFlags import RadarFlags
# from ..ImpdarError import ImpdarError
# from ..Picks import Picks
# from .. import gpslib


class radar(object):
    """
    the radar class holds the relevant information for a radar profile.
    keep track of processing steps with the flags attribute.
    """

    #: Attributes that every RadarData object should have.
    #: These should not be None.
    attrs_guaranteed = ['chan',
                        'data',
                        'decday',
                        'dt',
                        'pressure',
                        'snum',
                        'tnum',
                        'trace_int',
                        'trace_num',
                        'travel_time',
                        'trig',
                        'trig_level']

    #: Optional attributes that may be None without affecting processing.
    #: These may not have existed in old StoDeep files,
    #: and they often cannot be set at the initial data load.
    #: If they exist, they all have units of meters.
    attrs_optional = ['nmo_depth',
                      'lat',
                      'long',
                      'elev',
                      'dist',
                      'x_coord',
                      'y_coord',
                      'fn']

    # from ._RadarDataProcessing import reverse, nmo, crop, hcrop, restack, \
    #     rangegain, agc, constant_space, elev_correct, \
    #     constant_sample_depth_spacing, traveltime_to_depth
    # from ._RadarDataSaving import save, save_as_segy, output_shp, output_csv, \
    #     _get_pick_targ_info
    # from ._RadarDataFiltering import adaptivehfilt, horizontalfilt, highpass, \
    #     winavg_hfilt, hfilt, vertical_band_pass, denoise, migrate, \
    #     horizontal_band_pass, lowpass

    # Now make some load/save methods that will work with the matlab format
    def __init__(self, fn):
        # basic data file attributes
        #: str, file name
        self.fn = fn
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
        #: np.ndarray(tnum,) Optional.
        #: Projected x-coordinate along the profile.
        self.x_coord = None
        #: np.ndarray(tnum,) Optional.
        #: Projected y-coordinate along the profile.
        self.y_coord = None
        #: np.ndarray(tnum,) Optional.
        #: Depth of each trace below the surface
        self.nmo_depth = None
        #: np.ndarray(snum x tnum) processed radat data - this is what will actually be displayed, as to not modify original data
        self.proc_data = None
        #: np.ndarray(snum x tnum) clutter simulation
        self.clut = None
        #: pick object
        self.pick = pick()

        return

        self.check_attrs()


    def check_attrs(self):
        """Check if required attributes exist.

        This is largely for development only; loaders should generally call
        this method last, so that they can confirm that they have defined the
        necessary attributes.

        Raises
        ------
        ImpdarError
            If any required attribute is None,
            or any optional attribute is fully absent
        """
        # fn is required but defined separately
        for attr in self.attrs_guaranteed + ['fn']:
            if not hasattr(self, attr):
                raise ImpdarError('{:s} is missing. \
                    It appears that this is an ill-defined \
                        RadarData object'.format(attr))
            if getattr(self, attr) is None:
                raise ImpdarError('{:s} is None. \
                    It appears that this is an ill-defined \
                        RadarData object'.format(attr))

        for attr in self.attrs_optional:
            if not hasattr(self, attr):
                raise ImpdarError('{:s} is missing. \
                    It appears that this is an ill-defined \
                        RadarData object'.format(attr))

        # Do some shape checks, but we need to be careful since
        # variable-surface will screw this up
        if (self.data.shape != (self.snum, self.tnum)) and (self.elev is None):
            raise ImpdarError('The data shape does not match \
                              the snum and tnum values!!!')

        if hasattr(self, 'nmo_depth') and (self.nmo_depth is not None):
            if (self.nmo_depth.shape[0] != self.snum) and (self.elev is None):
                raise ImpdarError('The nmo_depth shape does not match \
                                  the tnum value!!!')

        # We checked for existence, so we can just confirm that these have
        # the right length if they exist
        for attr in ['lat', 'long', 'pressure', 'trig', 'elev', 'dist',
                     'x_coord', 'y_coord', 'decday']:
            if hasattr(self, attr) and getattr(self, attr) is not None:
                if (not hasattr(getattr(self, attr), 'shape')) or (
                        len(getattr(self, attr).shape) < 1):
                    if getattr(self, attr) == 0:
                        # This is just caused by None being weird with matlab
                        setattr(self, attr, None)
                    else:
                        if attr == 'trig':
                            self.trig = np.ones((self.tnum,), dtype=int) * int(self.trig)
                        else:
                            raise ImpdarError('{:s} needs to be a vector'.format(attr))
                elif getattr(self, attr).shape[0] != self.tnum:
                    raise ImpdarError('{:s} needs length tnum {:d}'.format(attr, self.tnum))

        if not hasattr(self, 'data_dtype') or self.data_dtype is None:
            self.data_dtype = self.data.dtype
        return

class pick(object):
    """
    pick class holds the relevant radar pick information.
    """
    # necessary pick objects:
    #     - ingested data file picks: surface and subsurf
    #     - current picks

    # methods:
    #     - interp
    #     - edit
    #     - delete

    def __init__(self):
        # necessary pick objects - pick dictionaries contain arrays of pick sample numbers at each trace in rdata
        #: dict, existing data file picks - these are picks already saved to file
        # data file picks are stored as twtt_surf and twtt_subsurf[n] arrays [np.ndarray(tnum,)]
        # containing twtt in second to a picked reflection horizon, and NaN where no pick exists
        # for a given trace. twtt_subsurf[n] is 0-indexed, representing individual pick segments/layers
        self.existing = {}
        #: dict, current session picks - these are new picks, not yet saved to file
        # current picks are stored as surf and subsurf[n] arrays [np.ndarray(tnum,)] containing 
        # the sample number of a picked reflection horizon, and NaN where no pick exists. 
        # subsurf[n] is 0-indexed,  representing individual pick segments/layers
        self.current = {}

        return