import numpy as np

class tools:
    # NOSEpick tools class
    #  - pick optimization based on windowed amplitude
    #  - trace viewing
    def __init__(self, master, lat, long, pickData):
        self.lat = lat
        self.long = long
        self.pickData = pickData

    def trace_view(self):
        # show individual trace view along with initial pick location

    def amp_window(self):
        # wubdiw initial pick sample to find max amplitude

