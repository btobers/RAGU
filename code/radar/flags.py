# RAGU - Radar Analysis Graphical Utility
#
# copyright © 2020 btobers <tobers.brandon@gmail.com>
#
# distributed under terms of the GNU GPL3.0 license
"""
rdata flags to hold the key information for a radar profile
"""

class flags(object):
    def __init__(self):
        # basic data file attributes
        #: sampzero, zero sample data setting following time zero adjustment
        self.sampzero = 0
        #: sim, bool clutter simulation present
        self.sim = False