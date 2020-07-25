#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2019 David Lilien <dlilien90@gmail.com>
#
# Distributed under terms of the GNU GPL3 license.

"""
Some classes and functions to handle different types of GPS data.

The workhorse of this library, nmea_info, is not designed to be created
directly. Use GPSdat class, which has an __init__ method, instead.

Additional methods in this library are used to read the filetypes from StoDeep.
These can then be used to redo the GPS info on another object
"""
import numpy as np
try:
    import osr
    conversions_enabled = True
except ImportError:
    conversions_enabled = False

from scipy.interpolate import interp1d

if conversions_enabled:
    def get_utm_conversion(lat, lon):
        """Retrun the gdal transform to convert coords."""
        def utm_getZone(longitude):
            return (int(1 + (longitude + 180.0) / 6.0))

        def utm_isNorthern(latitude):
            if (latitude < 0.0):
                return False
            else:
                return True

        utm_zone = utm_getZone(lon)
        is_northern = utm_isNorthern(lat)

        utm_cs = osr.SpatialReference()
        utm_cs.SetWellKnownGeogCS('WGS84')
        utm_cs.SetUTM(utm_zone, is_northern)

        # On newer versions of osr we need this, but on old versions it will fail
        try:
            utm_cs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        except AttributeError:
            pass

        wgs84_cs = utm_cs.CloneGeogCS()
        wgs84_cs.ExportToPrettyWkt()
        try:
            wgs84_cs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        except AttributeError:
            pass

        transform_WGS84_To_UTM = osr.CoordinateTransformation(wgs84_cs, utm_cs)
        return transform_WGS84_To_UTM.TransformPoints, utm_cs.ExportToPrettyWkt()

    def get_conversion(t_srs):
        out_cs = osr.SpatialReference()
        out_cs.SetFromUserInput(t_srs)
        try:
            out_cs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        except AttributeError:
            pass

        wgs84_cs = out_cs.CloneGeogCS()
        wgs84_cs.ExportToPrettyWkt()
        try:
            wgs84_cs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        except AttributeError:
            pass

        transform_WGS84_To_srs = osr.CoordinateTransformation(wgs84_cs, out_cs)
        return transform_WGS84_To_srs.TransformPoints, out_cs.ExportToPrettyWkt()
else:
    def get_utm_conversion(lat, lon):
        """Just raise an exception since we cannot really convert."""
        raise ImportError('Cannot convert coordinates: osr not importable')

    def get_conversion(t_srs):
        """Just raise an exception since we cannot really convert."""
        raise ImportError('Cannot convert coordinates: osr not importable')


def hhmmss2dec(times):
    """Deal with one of the many weird time formats. 6-char string to day."""
    s = times % 100
    m = (times % 10000 - s) / 100
    h = (times - m * 100 - s) / 10000
    return (h + m / 60.0 + s / 3600.0) / 24.0


class nmea_info:
    """Container for general information about lat, lon, etc.

    Attributes
    ----------
    lat: np.ndarray
        wgs84 latitude of points
    lon: np.ndarray_
        wgs84 longitude of points
    x: np.ndarray
        Projected x coordinates of points
    y: np.ndarray
        Projected y coordinates of points
    z: np.ndarray
        Projected z coordinates of points
    """

    all_data = None
    lat = None
    lon = None
    qual = None
    sats = None
    x = None
    y = None
    z = None
    geo_offset = None
    times = None
    scans = None

    def get_all(self):
        """Populate all the values from the input data."""
        self.glat()
        self.glon()
        self.gqual()
        self.gsats()
        self.gz()
        self.ggeo_offset()
        self.gtimes()
        if conversions_enabled:
            self.get_utm()

    def glat(self):
        """Populate lat(itude)."""
        if self.lat is None:
            self.lat = self.all_data[:, 2] * (
                (self.all_data[:, 1] - self.all_data[:, 1] % 100) / 100 + (
                    self.all_data[:, 1] % 100) / 60)
        if self.y is None:
            self.y = self.lat * 110000.0  # Temporary guess using earths radius
        return self.lat

    def glon(self):
        """Populate lon(gitude)."""
        if self.lon is None:
            self.lon = self.all_data[:, 4] * (
                (self.all_data[:, 3] - self.all_data[:, 3] % 100) / 100 + (
                    self.all_data[:, 3] % 100) / 60)
        if self.x is None:
            # Temporary guess using radius of the earth
            if self.lat is None:
                self.glat()
            self.x = self.lon * 110000.0 * \
                np.abs(np.cos(self.lat * np.pi / 180.0))
        return self.lon

    def gqual(self):
        """Populate qual(ity)."""
        self.qual = self.all_data[:, 5]
        return self.qual

    def gsats(self):
        """Populate sats (number of satellites)."""
        self.sats = self.all_data[:, 6]
        return self.sats

    def gz(self):
        """Populate z (elevation)."""
        self.z = self.all_data[:, 8]
        return self.z

    def ggeo_offset(self):
        """Populate geo_offset (Distance between ellipsoid and geoid)."""
        self.geo_offset = self.all_data[:, 8]
        return self.geo_offset

    def gtimes(self):
        """Populate times."""
        self.times = self.all_data[:, 0]
        return self.times

    def get_utm(self):
        """Transform lat and lon to utm coords in a nice way."""
        transform, _ = get_utm_conversion(np.nanmean(self.lat),
                                          np.nanmean(self.lon))
        pts = np.array(transform(np.vstack((self.lon, self.lat)).transpose()))
        self.x, self.y = pts[:, 0], pts[:, 1]

    @property
    def dectime(self):
        """Convert the nasty 6-char time to something usable."""
        return hhmmss2dec(self.times)


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
        self.nmea_info = nmea_all_info(gga)
        self.nmea_info.scans = scans
        self.nmea_info.get_all()
        kgps_mask = np.logical_and(~np.isnan(self.nmea_info.times[1:]),
                                   np.diff(self.nmea_info.scans) != 0)
        kgps_mask = np.logical_and(np.diff(self.nmea_info.times) != 0,
                                   kgps_mask)
        kgps_where = np.where(kgps_mask)[0]
        kgps_indx = np.hstack((np.array([0]), 1 + kgps_where))
        self.lat = interp1d(self.nmea_info.scans[kgps_indx],
                            self.nmea_info.lat[kgps_indx],
                            kind='linear',
                            fill_value='extrapolate')(np.arange(trace_num))
        self.lon = interp1d(self.nmea_info.scans[kgps_indx],
                            self.nmea_info.lon[kgps_indx],
                            kind='linear',
                            fill_value='extrapolate')(np.arange(trace_num))
        self.z = interp1d(self.nmea_info.scans[kgps_indx],
                          self.nmea_info.z[kgps_indx], kind='linear',
                          fill_value='extrapolate')(np.arange(trace_num))
        self.times = interp1d(self.nmea_info.scans[kgps_indx],
                              self.nmea_info.times[kgps_indx],
                              kind='linear',
                              fill_value='extrapolate')(trace_num)