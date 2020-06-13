import numpy as np
import tkinter as tk
import sys, h5py

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
def savePick(fpath, f_saveName, data, subsurf_pick_dict, eps):
    # fpath is the data file path [str]
    # f_saveName is the path for where the exported csv pick file should be saved [str]
    # data is the data file structure [dict]
    # subsurf_pick_dict contains the subsurface pick indeces - each key is an array the length of the number of traces, with np.nan where no picks were made [dict]
    # eps is a value for the dielectric constant used to calculate ice thickness based on EM wave speed [float]
    c = 299792458               # Speed of light at STP
    v = c/(np.sqrt(eps))        # EM wave veloity in ice - for thickness calculation

    trace = np.arange(data["num_trace"])                # array to hold trace number
    lon = data["navdat"].navdat[:,0]                    # array to hold longitude
    lat = data["navdat"].navdat[:,1]                    # array to hold latitude
    elev_air = data["navdat"].navdat[:,2]               # array to hold aircraft elevation
    surf_idx = data["surf_idx"]                         # array to hold index of surface from either manual picks, or altimetry dataset
    twtt_surf = data["twtt_surf"]                       # array to hold twtt to surface below nadir position
    subsurf_idx_pk = np.repeat(np.nan,lon.shape[0])     # array to hold indeces of picks
    twtt_bed = np.repeat(np.nan,lon.shape[0])           # array to hold twtt to pick indeces
    thick = np.repeat(np.nan,lon.shape[0])              # array to hold derived thickness from picks
    elev_gnd = np.repeat(np.nan,lon.shape[0])           # array to hold ground(surface) elevation
    elev_bed = np.repeat(np.nan,lon.shape[0])           # array to hold derived bed elevation from picks

    # iterate through subsurf_pick_dict layers adding data to export arrays
    for _i in range(len(subsurf_pick_dict)):
        picked_traces = np.where(~np.isnan(subsurf_pick_dict[str(_i)]))[0]

        subsurf_idx_pk[picked_traces] = subsurf_pick_dict[str(_i)][picked_traces]

        twtt_bed[picked_traces] = subsurf_pick_dict[str(_i)][picked_traces]*data["dt"]    # convert pick idx to twtt

        # calculate ice thickness - using twtt_bed and twtt_surf
        thick[picked_traces] = ((((subsurf_pick_dict[str(_i)][picked_traces]*data["dt"]) - (data["twtt_surf"][picked_traces])) * v) / 2)

    # calculate gnd elevation 
    elev_gnd = [a-(b*c/2) for a,b in zip(elev_air,twtt_surf)]

    # calculate bed elevation
    elev_bed = [a-b for a,b in zip(elev_gnd,thick)]

    # if twtt_surf not in data, replace values for twtt_surf, elev_gnd, elev_bed, and thick with NaN's to be recalculated later
    if not np.any(data["twtt_surf"]):
        twtt_surf = np.repeat(np.nan,lon.shape[0])
        thick = np.repeat(np.nan,lon.shape[0])
        elev_gnd = np.repeat(np.nan,lon.shape[0])
        elev_bed = np.repeat(np.nan,lon.shape[0])

    try:
        # combine the data into a matrix for export
        dstack = np.column_stack((trace,lon,lat,elev_air,elev_gnd,surf_idx,twtt_surf,subsurf_idx_pk,twtt_bed,elev_bed,thick))

        header = "trace,lon,lat,elev_air,elev_gnd,surf_idx,twtt_surf,subsurf_idx_pk,twtt_bed,elev_bed,thick"
        np.savetxt(f_saveName, dstack, delimiter=",", newline="\n", fmt="%s", header=header, comments="")

        # reopen hdf5 file to save pick twtt_bed as dataset within ["drv/pick"]
        f = h5py.File(fpath, "a") 
        num_file_pick_lyr = data["num_file_pick_lyr"]
        # save the new subsurface pick to the hdf5 file - determine whther to overwrite or append
        if (num_file_pick_lyr > 0) and (tk.messagebox.askyesno("overwrite/append","overwrite most recent picks previously saved to file (no to append as new subsurface pick layer)?") == True):
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
    f =  h5py.File(fpath, "a")
    for _i in range(num_file_pick_lyr):
        del f["drv/pick"]["twtt_subsurf" + str(_i)]
    f.close()


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
def twtt2depth(a, eps=3.15):
    c = 299792458                   # Speed of light at STP
    v = c/np.sqrt(eps)
    depth = a*v/(2*1000)            # convert input twtt to distance in km
    return depth


# depth2twtt function
def depth2twtt(a, eps=3.15):
    c = 299792458                   # Speed of light at STP
    v = c/np.sqrt(eps)
    twtt = a*2*1e3/v                # convert input depth to meters, then return twtt
    return twtt

# twtt2sample
def twtt2sample(array, dt):
    sample_array = np.rint(array / dt)
    return sample_array

# sample2twtt
def sample2twtt(array, dt):
    twtt_array = array * dt
    return twtt_array