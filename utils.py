import numpy as np
import tkinter as tk
import sys, h5py
from constants import *

# calculate total euclidian distance along a line
def euclid_dist(nav):
    dist = np.zeros(nav.navdat.shape[0])
    for _i in range(len(dist)):
        if _i>=1:
            dist[_i] = dist[_i-1] + np.sqrt((nav.navdat[_i,0] - nav.navdat[_i-1,0])**2 + (nav.navdat[_i,1] - nav.navdat[_i-1,1])**2)
    # convert to km
    dist = dist*1e-3

    return dist


# a set of utility functions for NOSEpick GUI
# need to clean up this entire utility at some point
def savePick(fpath, f_saveName, data, subsurf_pick_dict, eps_r):
    # fpath is the data file path [str]
    # f_saveName is the path for where the exported csv pick file should be saved [str]
    # data is the data file structure [dict]
    # subsurf_pick_dict contains the subsurface pick indeces - each key is an array the length of the number of traces, with np.nan where no picks were made [dict]
    # eps_r is a value for the dielectric constant used to calculate ice thickness based on EM wave speed [float]
    v = C/(np.sqrt(eps_r))        # EM wave veloity in ice - for thickness calculation

    trace = data["trace"]                # array to hold trace number
    lon = data["navdat"].navdat[:,0]                    # array to hold longitude
    lat = data["navdat"].navdat[:,1]                    # array to hold latitude
    elev_air = data["navdat"].navdat[:,2]               # array to hold aircraft elevation
    twtt_surf = data["pick"]["twtt_surf"]               # array to hold twtt to surface below nadir position
    elev_gnd = data["elev_gnd"]                         # array to hold ground elevation beneath aircraft sampled from lidar pointcloud
    surf_idx = data["surf_idx"]                         # array to hold surface index
    subsurf_idx_pk = np.repeat(np.nan,lon.shape[0])     # array to hold indeces of picks

    # iterate through subsurf_pick_dict layers adding data to export arrays
    for _i in range(len(subsurf_pick_dict)):
        picked_traces = np.where(~np.isnan(subsurf_pick_dict[str(_i)]))[0]

        subsurf_idx_pk[picked_traces] = subsurf_pick_dict[str(_i)][picked_traces]

    # convert pick idx to twtt
    twtt_bed = subsurf_idx_pk * data["dt"]    

    # calculate ice thickness
    thick = (((twtt_bed - twtt_surf) * v) / 2)

    # calculate bed elevation
    elev_bed = elev_gnd - thick

    try:
        # combine the data into a matrix for export
        dstack = np.column_stack((trace,lon,lat,elev_air,elev_gnd,surf_idx,twtt_surf,subsurf_idx_pk,twtt_bed,elev_bed,thick))

        header = "trace,lon,lat,elev_air,elev_gnd,surf_idx,twtt_surf,subsurf_idx_pk,twtt_bed,elev_bed,thick"
        np.savetxt(f_saveName, dstack, delimiter=",", newline="\n", fmt="%s", header=header, comments="")

        if fpath.endswith(".h5"):
            # reopen hdf5 file to save pick twtt_bed as dataset within ["drv/pick"]
            f = h5py.File(fpath, "a") 
            num_file_pick_lyr = data["num_file_pick_lyr"]
            # save the new subsurface pick to the hdf5 file - determine whther to overwrite or append
            if (num_file_pick_lyr > 0) and (tk.messagebox.askyesno("overwrite picks","overwrite most recent subsurface picks previously exported to data file (no to append as new subsurface pick layer)?") == True):
                del f["drv/pick"]["twtt_subsurf" + str(num_file_pick_lyr - 1)]
                twtt_subsurf_pick = f["drv"]["pick"].require_dataset("twtt_subsurf" + str(num_file_pick_lyr - 1), data=twtt_bed, shape=twtt_bed.shape, dtype=np.float32)
            else:
                twtt_subsurf_pick = f["drv"]["pick"].require_dataset("twtt_subsurf" + str(num_file_pick_lyr), data=twtt_bed, shape=twtt_bed.shape, dtype=np.float32)

            twtt_subsurf_pick.attrs.create("Unit", np.string_("Seconds"))
            twtt_subsurf_pick.attrs.create("Source", np.string_("Manual pick layer"))
            f.close()
        print("picks exported successfully")

    except Exception as err:
        print("picks export error:" + str(err))


def delete_savedPicks(fpath, num_file_pick_lyr):
    if fpath.endswith("h5"):
        f =  h5py.File(fpath, "a")
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


def find_nearest(array,value):
    # return index in array with value closest to the passed value
    idx = (np.abs(array-value)).argmin()
    return idx


# interp array is a function which linearly interpolates over an array of data between unique values
def interp_array(array):
    # initialize list of xp and fp coordinates for np.interp
    xp = []
    fp = []
    # initialize value to determine if preceeding array value equals the previous value
    v = -9999
    # iterate through array
    # if current value is not equal to previous value append the current index to xp, and the value to fp
    # update the value
    for _i in range(len(array)):
        if(array[_i] != v):
            xp.append(_i)
            fp.append(array[_i])
            v = array[_i]

    # update last value of xp
    xp[-1] = len(array)-1
    # declare indeces to interpolate over
    x = np.arange(0, len(array))
    # interpolate over array
    array_interp = np.interp(x, xp, fp)
    return array_interp


# export the pick image
# need to figure out a better way to set extent so that it's not screen specific
# also need to hold back image from being displayed in app temporarily when saved
def exportIm(fname, fig, extent=None):
    fig.savefig(fname.rstrip(".csv") + ".png", dpi = 500, bbox_inches='tight', pad_inches = 0.05, transparent=True)# facecolor = "#d9d9d9")


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


def print_pickInfo(data, trace, sample):
    v = C/(np.sqrt(3.15))        # EM wave veloity in ice - for thickness calculation

    fields = ["trace","sample","elev_air","twtt_surf","elev_gnd","twtt_bed","elev_bed","thick"]

    elev_air = data["navdat"].navdat[trace,2]
    twtt_surf = data["pick"]["twtt_surf"][trace]
    elev_gnd = data["elev_gnd"][trace]
    twtt_bed = sample * data["dt"]
    thick = (((twtt_bed - twtt_surf) * v) / 2)
    elev_bed = elev_gnd - thick

    print(*fields, sep="\t")
    print("%d\t%d\t%8.4f\t%8.4e\t%8.4f\t%8.4e\t%8.4f\t%8.4f" % (trace,sample,elev_air,twtt_surf,elev_gnd,twtt_bed,elev_bed,thick))
    print()