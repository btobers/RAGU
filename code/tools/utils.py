# NOSEpick - Nearly Optimal Subsurface Extractor
#
# copyright © 2020 btobers <tobers.brandon@gmail.com>
#
# distributed under terms of the GNU GPL3.0 license
"""
utility functions for NOSEpick GUI
"""
### imports ###
import numpy as np
import pandas as pd
import geopandas as gpd
import tkinter as tk
import sys, h5py, fnmatch
from tools.constants import *

# remove_outliers is a function to remove outliers from an array
# returns bool array
def remove_outliers(array):
    mean = np.mean(array)
    standard_deviation = np.std(array)
    distance_from_mean = abs(array - mean)
    max_deviations = 2
    not_outlier = distance_from_mean < max_deviations * standard_deviation
    return not_outlier


# delete_savedPicks is a method to clear saved picks from an hdf5 data file
def delete_savedPicks(fpath):
    if fpath.endswith("h5"):
        f =  h5py.File(fpath, "a")
        num_file_pick_lyr = len(fnmatch.filter(f["drv"]["pick"].keys(), "twtt_subsurf*"))
        for _i in range(num_file_pick_lyr):
            del f["drv/pick"]["twtt_subsurf" + str(_i)]
        f.close()


# list_insert is a function to return the element at which to insert a new item to a sorted list
def list_insert_idx(list, n): 
    # search for the position 
    for i in range(len(list)): 
        if list[i] > n: 
            index = i 
            break
    return index


# find nearest value in array to arg
def find_nearest(a, val):
    idx = (np.abs(a - val)).argmin()
    return idx


# nan_array_equal is a method to determine if two arrays which may contain nan values are equivalent
def nan_array_equal(a, b):
    try:
        return ((a == b) | (np.isnan(a) & np.isnan(b))).all()
    except ValueError:
        return


# dict_compare is a method to compare the two pick dictionaries to see if they are equal
def dict_compare(a, b):
    if len(a) == 0 & len(b) == 0:
        return True
    else:
        for _i in range(len(a)):
            if nan_array_equal(a[str(_i)],b[str(_i)]):
                return True
        return False


# srfpick2elev function
def srfpick2elev(a, b, tnum, dt):
    """
    calculate surface elevation from updated surface pick, subtracting distance form navdf["elev"] to surface
    #: np.ndarray(tnum,) a, surface index per trace [samle #]
    #: np.ndarray(tnum,) b, radar elevation per trace [m.a.s.l.]
    #: int tnum, the number of traces in the file
    #: float dt, spacing between samples in travel time [seconds]
    """
    if a.shape == (tnum,):
        dist = twtt2depth(sample2twtt(a, dt), eps_r=1)
        gndElev = b - dist

        return gndElev


# twtt2depth function
def twtt2depth(a, eps_r=3.15):
    v = C/np.sqrt(eps_r)
    depth = a*v/(2)            # convert input twtt to distance in km
    return depth


# depth2twtt function
def depth2twtt(a, eps_r=3.15):
    v = C/np.sqrt(eps_r)
    twtt = a*2/v                # convert input depth to meters, then return twtt
    return twtt


# twtt2sample
def twtt2sample(array, dt):
    sample_array = np.rint(array / dt)
    return sample_array


# sample2twtt
def sample2twtt(array, dt):
    twtt_array = array * dt
    return twtt_array


# amp2powdB
def amp2powdB(array):
    tmp = np.power(array,2)
    # mask zero-power values
    tmp[tmp == 0] = np.nan
    out = 10*np.log10(tmp)
    return out


# powdB2amp
def powdB2amp(array):
    return np.power(10, (array / 20))


# pkampwind
def pkampwind(array, idx, windsize):
    # loop through array columns and find peak greater than 1  row idx within window of given idx
    # use gradient to find maximum index where absolute value of derivative is greater than 1 sigma
    out = np.repeat(np.nan, array.shape[1])
    grad = np.gradient(array, axis = 1)
    std = np.std(array, axis = 0)
    for _i in range(array.shape[1]):
        if np.isnan(idx[_i]):
            continue
        out[_i] = int(idx[_i] - (windsize/2)) + np.argmax(np.abs(grad[int(idx[_i] - (windsize/2)):int(idx[_i] + (windsize/2)), _i]) > std[_i])
    return out


def print_pickInfo(data, trace, sample):
    v = C/(np.sqrt(3.15))        # EM wave veloity in ice - for thickness calculation

    fields = ["trace","sample","alt","gndElev","srfTwtt","subsrfTwtt","subsrfElev","thick"]

    if not np.isnan(data.pick.current_surf).all():
        srfTwtt = sample2twtt(data.pick.current_surf[trace],data.dt)
    else:
        srfTwtt = data.pick.existing_twttSurf[trace]
    alt = data.navdf["elev"].iloc[trace]    
    gndElev = data.gndElev[trace]
    subsrfTwtt = sample * data.dt
    thick = (((subsrfTwtt - srfTwtt) * v) / 2)
    subsrfElev = gndElev - thick

    print(*fields, sep="\t\t")
    print("%d\t\t%d\t\t%8.4f\t\t%8.4e\t\t%8.4f\t\t%8.4e\t\t%8.4f\t\t%8.4f" % (trace,sample,alt,gndElev,srfTwtt,subsrfTwtt,subsrfElev,thick))
    print()