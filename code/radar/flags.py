# NOSEpick - Nearly Optimal Subsurface Extractor
#
# copyright © 2020 btobers <tobers.brandon@gmail.com>
#
# distributed under terms of the GNU GPL3.0 license.
### imports ###

class flags(object):
    """
    the flags class holds the key information for a radar profile.
    """
    def __init__(self):
        # basic data file attributes
        #: sampzero, zero sample data setting following time zero adjustment
        self.sampzero = 0
        