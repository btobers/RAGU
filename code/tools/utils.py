### imports ###
import numpy as np
import tkinter as tk
import sys, h5py, fnmatch
from tools.constants import *
"""
utility functions for NOSEpick GUI
"""

def export_pk_csv(f_saveName, rdata, eps_r, amp_out = False):
    # f_saveName is the path for where the exported csv pick file should be saved [str]
    # rdata object
    # eps_r is a value for the dielectric constant used to calculate ice thickness based on EM wave speed [float]
    # amp_out dictates whether or not to export amplitude of picks [bool]
    v = C/(np.sqrt(eps_r))                      # wave veloity

    trace = np.arange(rdata.tnum)               # array to hold trace number
    lon = rdata.navdf["lon"]                    # array to hold longitude
    lat = rdata.navdf["lat"]                    # array to hold latitude
    alt = rdata.navdf["elev"]                   # array to hold aircraft elevation
    elev_gnd = rdata.elev_gnd                   # array to hold ground elevation beneath aircraft sampled from lidar pointcloud
    subsurf_pk = np.repeat(np.nan, rdata.tnum)  # array to hold indeces of subsurface picks

    # if existing surface pick, and no current -> use existing
    if np.isnan(rdata.pick.current.surf).all() and not np.isnan(rdata.pick.existing.twtt_surf).all():
        twtt_surf = rdata.pick.existing.twtt_surf
        surf = twtt2sample(twtt_surf, rdata.dt)

    else:
        surf = rdata.pick.current.surf
        twtt_surf = sample2twtt(surf, rdata.dt)

    # iterate through pick segments adding data to export arrays
    for _i in rdata.pick.current.subsurf.keys():
        picked_traces = np.where(~np.isnan(rdata.pick.current.subsurf[str(_i)]))[0]

        subsurf_pk[picked_traces] = rdata.pick.current.subsurf[str(_i)][picked_traces]

    # convert pick sample to twtt
    twtt_bed = subsurf_pk * rdata.dt    

    # calculate ice thickness
    thick = (((twtt_bed - twtt_surf) * v) / 2)

    # calculate bed elevation
    elev_bed = elev_gnd - thick

    try:
        # combine the data into a matrix for export
        if amp_out:
            # if raw data is complex, take abs value to get amplitude
            if not np.isreal(rdata.dat).all():
                amp = np.abs(rdata.dat)
            else:
                amp = rdata.dat

            # export surface and subsurface pick amplitude values
            idx = ~np.isnan(surf)
            surf_amp = np.repeat(np.nan, rdata.tnum)
            surf_amp[idx] = amp[surf[idx].astype(np.int),idx]

            idx = ~np.isnan(subsurf_pk)
            subsurf_amp = np.repeat(np.nan, rdata.tnum)
            subsurf_amp[idx] = amp[subsurf_pk[idx].astype(np.int),idx]

            dstack = np.column_stack((trace,lon,lat,alt,elev_gnd,twtt_surf,surf_amp,twtt_bed,subsurf_amp,elev_bed,thick))
            header = "trace,lon,lat,alt,elev_gnd,twtt_surf,surf_amp,twtt_bed,subsurf_amp,elev_bed,thick"
        else:
            dstack = np.column_stack((trace,lon,lat,alt,elev_gnd,twtt_surf,twtt_bed,elev_bed,thick))
            header = "trace,lon,lat,alt,elev_gnd,twtt_surf,twtt_bed,elev_bed,thick"

        if np.array_equal(alt, elev_gnd):
            # remove alt if ground-based data and update header
            dstack = np.delete(dstack, 4, 1)
            header = header.replace(",alt","").replace("elev_gnd","elev")

        np.savetxt(f_saveName, dstack, delimiter=",", newline="\n", fmt="%s", header=header, comments="")

        if rdata.fpath.endswith(".h5") and (tk.messagebox.askyesno("export picks", "save picks to data file?") == True):
            export_pk_h5(rdata.fpath, twtt_bed)

        print("picks exported successfully")

    except Exception as err:
        print("picks export error:" + str(err))


# method to save twtt_bed pick to h5 data file
def export_pk_h5(fpath, twtt_bed):
    f = h5py.File(fpath, "a") 
    num_file_pick_lyr = len(fnmatch.filter(f["drv"]["pick"].keys(), "twtt_subsurf*"))
    # save the new subsurface pick to the hdf5 file - determine whther to overwrite or append
    if (num_file_pick_lyr > 0) and (tk.messagebox.askyesno("overwrite picks","overwrite most recent subsurface picks previously exported to data file (no to append as new subsurface pick layer)?") == True):
        del f["drv"]["pick"]["twtt_subsurf" + str(num_file_pick_lyr - 1)]
        twtt_subsurf_pick = f["drv"]["pick"].require_dataset("twtt_subsurf" + str(num_file_pick_lyr - 1), data=twtt_bed, shape=twtt_bed.shape, dtype=np.float32)
    else:
        twtt_subsurf_pick = f["drv"]["pick"].require_dataset("twtt_subsurf" + str(num_file_pick_lyr), data=twtt_bed, shape=twtt_bed.shape, dtype=np.float32)

    twtt_subsurf_pick.attrs.create("Unit", np.string_("Seconds"))
    twtt_subsurf_pick.attrs.create("Source", np.string_("Manual pick layer"))
    f.close()


# export the pick image
# need to figure out a better way to set extent so that it's not screen specific
# also need to hold back image from being displayed in app temporarily when saved
def exportIm(fname, fig, extent=None):
    fig.savefig(fname.rstrip(".csv") + ".png", dpi = 500, bbox_inches='tight', pad_inches = 0.05, transparent=True)# facecolor = "#d9d9d9")


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


# nan_array_equal is a method to determine if two arrays which may contain nan values are equivalent
def nan_array_equal(a, b):
    return ((a == b) | (np.isnan(a) & np.isnan(b))).all()


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