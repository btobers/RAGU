# RAGU - Radar Analysis Graphical Utility
#
# copyright © 2020 btobers <tobers.brandon@gmail.com>
#
# distributed under terms of the GNU GPL3.0 license
"""
utility functions for RAGU
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


# sort dictionary full of numpy arrays using array mean value
def sort_array_dict(a):
    out = {}
    mean_dict = {}
    for key, arr in a.items():
        mean_dict[key] = np.nanmean(arr)
    keys = [k for k, v in sorted(mean_dict.items(), key=lambda item: item[1])]
    for key in keys:
        out[key] = a[key]
    return out


# nonan_idx_array returns an array with the index of non-nan values
def nonan_idx_array(a):
    out = np.repeat(np.nan, a.shape[0])
    mask = np.where(~np.isnan(a))[0]
    out[mask] = mask
    return out


# nan_array_equal is a method to determine if two arrays which may contain nan values are equivalent
def nan_array_equal(a, b):
    try:
        return ((a == b) | (np.isnan(a) & np.isnan(b))).all()
    except ValueError:
        return


def nan_array_sum(a, axis=0):
    """
    sum across an array with nans, treating the nan's as zero unless all elements across specified axis are nan
    INPUT:
    a           data array
    axis        axis to sum across

    OUTPUT:
    out         summed output array
    """
    out = np.nansum(a,axis=axis)
    out[np.all(np.isnan(a), axis=axis)] = np.nan    
    return out


def merge_paths(a):
    """
    merge picks from all segment paths in horizon dicitonary
    INPUT:
    a           dictionary containing impick path objects for each key 

    OUTPUT:
    (x,y)       tuple of x,y merged path data
    """
    l = list(a.values())
    x = nan_array_sum(np.stack([path.x for path in l]))
    y = nan_array_sum(np.stack([path.y for path in l]))
    return (x,y)


# dict_compare is a method to compare the two pick dictionaries to see if they are equal
def dict_compare(a, b):
    if len(a) == 0 & len(b) == 0:
        return True
    else:
        for _i in range(len(a)):
            if nan_array_equal(a[_i],b[_i]):
                return True
        return False


# surfpick2elev function
def surfpick2elev(a, b, tnum, dt):
    """
    calculate surface elevation from updated surface pick, subtracting distance form navdf["elev"] to surface
    #: np.ndarray(tnum,) a, surface index per trace [samle #]
    #: np.ndarray(tnum,) b, radar elevation per trace [m.a.s.l.]
    #: int tnum, the number of traces in the file
    #: float dt, spacing between samples in travel time [seconds]
    """
    if a.shape == (tnum,):
        dist = twtt2depth(sample2twtt(a, dt), eps_r=1)
        surfElev = b - dist

        return surfElev


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


def print_pickInfo(data, trace, sample, eps_r=3.15):
    v = C/(np.sqrt(eps_r))        # EM wave veloity in ice - for thickness calculation

    if not np.isnan(data.pick.current_surf).all():
        surfTwtt = sample2twtt(data.pick.current_surf[trace],data.dt)
    else:
        surfTwtt = data.pick.existing_twttSurf[trace]
    alt = data.navdf["elev"].iloc[trace]    
    surfElev = data.surfelev[trace]
    subsurfTwtt = sample * data.dt
    thick = (((subsurfTwtt - surfTwtt) * v) / 2)
    subsurfelev = surfelev - thick

    print("trace:\t\t",trace)
    print("sample:\t\t",sample)
    print("alt:\t\t%8.2f" % (alt))
    print("surfelev:\t\t%8.2f" % (surfelev))
    print("surfTwtt:\t\t%8.2e" % (surfTwtt))
    print("subsurfTwtt:\t\t%8.2e" % (subsurfTwtt))
    print("subsurfelev:\t\t%8.2f" % (subsurfelev))
    print("thick:\t\t%8.2f" % (thick))
    print()
