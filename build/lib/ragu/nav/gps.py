"""
gps library contains classes and functions to handle different types of GPS data
modified from ImpDAR - DOI:10.5281/zenodo.3833057
"""
### imports ###
import numpy as np
from scipy.interpolate import interp1d
import matplotlib.pyplot as plt
import sys

class nmea_info:
    """Container for general information about lat, lon, etc.

    Attributes
    ----------
    lat: np.ndarray
        wgs84 latitude of points
    lon: np.ndarray_
        wgs84 longitude of points
    elev: np.ndarray
        elevation
    """

    all_data = None
    lat = None
    lon = None
    elev = None
    times = None
    scans = None

    def get_all(self):
        """Populate all the values from the input data."""
        self.glat()
        self.glon()
        self.ghgt()
        self.gtimes()

    def glat(self):
        """Populate lat(itude)."""
        if self.lat is None:
            self.lat = self.all_data[:, 2] * (
                (self.all_data[:, 1] - self.all_data[:, 1] % 100) / 100 + (
                    self.all_data[:, 1] % 100) / 60)
        return self.lat

    def glon(self):
        """Populate lon(gitude)."""
        if self.lon is None:
            self.lon = self.all_data[:, 4] * (
                (self.all_data[:, 3] - self.all_data[:, 3] % 100) / 100 + (
                    self.all_data[:, 3] % 100) / 60)
        return self.lon

    def ghgt(self):
        """Populate z (elevation)."""
        self.elev = self.all_data[:, 8]
        return self.elev

    def gtimes(self):
        """Populate times."""
        self.times = self.all_data[:, 0]
        return self.times


def nmea_all_info(list_of_sentences):
    """
    Return an object with the nmea info from a given list of sentences.

    Parameters
    ----------
    list_of_sentences : list of strs
        NMEA output.

    Raises
    ------
    ValueError
        If the NMEA output does not contain GGA strings.

    Returns
    -------
    np.ndarray
        An array of the useful information in the NMEA sentences.
    """
    def _gga_sentence_split(sentence):
        all = sentence.split(',')
        if len(all) > 5:
            numbers = list(map(lambda x: float(x) if x != '' else 0, all[1:3] + [1] + [all[4]] + [1] + all[6:10] + [all[11]]))
            if all[3] == 'S':
                numbers[2] = -1
            if all[5] == 'W':
                numbers[4] = -1
        elif len(all) > 2:
            numbers = list(map(lambda x: float(x) if x != '' else 0, all[1:3] + [1]))
            if all[3] == 'S':
                numbers[2] = -1
        else:
            numbers = np.nan
        return numbers

    if list_of_sentences[0].split(',')[0] == '$GPGGA':
        data = nmea_info()
        data.all_data = np.array([_gga_sentence_split(sentence)
                                  for sentence in list_of_sentences])
        return data
    else:
        print(list_of_sentences[0].split(',')[0])
        raise ValueError('I can only do gga sentences right now')


class GPSdat(nmea_info):
    """
    A container to make nmea info useful.

    This should handle frequency mismatch between radar and gps.

    Parameters
    ----------
    gga : list of strs
        The GPS data
    scans : list of floats
        traces in radargram for which gps data was acquired
    trace_num : np array
        array of traces in radar data over which to interpolate sparse gps data

    Returns
    -------
    None.

    """

    def __init__(self, gga, scans, trace_num):
        # parse recorded nmea strings
        self.nmea_info = nmea_all_info(gga)
        self.nmea_info.scans = scans
        self.nmea_info.get_all()
        # get time stamps where data recorded to interpolate between
        kgps_mask = np.logical_and(~np.isnan(self.nmea_info.times[1:]),
                                   np.diff(self.nmea_info.scans) != 0)
        kgps_mask = np.logical_and(np.diff(self.nmea_info.times) != 0,
                                   kgps_mask)
        kgps_where = np.where(kgps_mask)[0]
        kgps_indx = np.hstack((np.array([0]), 1 + kgps_where))
        # linearly interpolate lat,lon,elev,time - linearly extrapolate to fill tails 
        self.lat = interp1d(self.nmea_info.scans[kgps_indx],
                            self.nmea_info.lat[kgps_indx],
                            kind='linear',
                            fill_value='extrapolate')(np.arange(trace_num))
        self.lon = interp1d(self.nmea_info.scans[kgps_indx],
                            self.nmea_info.lon[kgps_indx],
                            kind='linear',
                            fill_value='extrapolate')(np.arange(trace_num))
        self.elev = interp1d(self.nmea_info.scans[kgps_indx],
                          self.nmea_info.elev[kgps_indx], kind='linear',
                          fill_value='extrapolate')(np.arange(trace_num))
        self.times = interp1d(self.nmea_info.scans[kgps_indx],
                              self.nmea_info.times[kgps_indx],
                              kind='linear',
                              fill_value='extrapolate')(np.arange(trace_num))