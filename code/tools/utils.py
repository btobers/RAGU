### imports ###
import numpy as np
import pandas as pd
import geopandas as gpd
import tkinter as tk
import sys, h5py, fnmatch
from tools.constants import *
"""
utility functions for NOSEpick GUI
"""
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
def amp2powdB(amparray):
    powarray = np.power(amparray,2)
    # mask zero-power values
    powarray[powarray == 0] = np.nan
    dBarray = 10*np.log10(powarray)
    return dBarray


def print_pickInfo(data, trace, sample):
    v = C/(np.sqrt(3.15))        # EM wave veloity in ice - for thickness calculation

    fields = ["trace","sample","alt","twtt_surf","elev_gnd","twtt_bed","elev_bed","thick"]

    alt = data["navdat"].navdat[trace,2]
    twtt_surf = data["pick"]["twtt_surf"][trace]
    elev_gnd = data["elev_gnd"][trace]
    twtt_bed = sample * data["dt"]
    thick = (((twtt_bed - twtt_surf) * v) / 2)
    elev_bed = elev_gnd - thick

    print(*fields, sep="\t")
    print("%d\t%d\t%8.4f\t%8.4e\t%8.4f\t%8.4e\t%8.4f\t%8.4f" % (trace,sample,alt,twtt_surf,elev_gnd,twtt_bed,elev_bed,thick))
    print()