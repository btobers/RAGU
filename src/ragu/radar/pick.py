# RAGU - Radar Analysis Graphical Utility
#
# copyright © 2020 btobers <tobers.brandon@gmail.com>
#
# distributed under terms of the GNU GPL3.0 license
"""
rdata pick ojects
"""
import numpy as np

class pick(object):
    """
    pick class holds the relevant radar pick information.
    """
    def __init__(self):
        #: dict horizons, nested containing  file pick horizons
        # each horizon is itself a dictionary with each key 
        # of type np.ndarray(tnum,), representing the
        # pick in sample number for each trace
        self.horizons = {}
        #: str srf, surface horizon name
        self.srf = None

        return


    # set_srf defines the surface horizon name
    def set_srf(self, srf=None):
        self.srf = srf


    # get_srf returns the defined surface horizon name
    def get_srf(self):
        return self.srf


    # get_pick_flag returns true if interpretations exist, false otherwise
    def get_pick_flag(self):
        flag = False
        for key, item in self.horizons.items():
            if np.isnan(item).all():
                continue
            else:
                flag = True
                break

        return flag