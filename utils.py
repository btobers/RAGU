import numpy as np
import sys

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
def savePick(f_saveName, data, pick_dict):
    # f_saveName is the path for where the exported csv pick file should be saved [str]
    # data is the data file structure [dict]
    # pick_dict contains the subsurface pick indeces - each key is an array the length of the number of traces, with -1 where no picks were made [dict]
    f_saveName = f_saveName
    data = data
    pick_dict = pick_dict

    v_ice = 3e8/(np.sqrt(3.15))   # EM wave veloity in ice - for thickness calculation

    trace = np.arange(data["num_trace"])            # array to hold trace number
    lon = data["navdat"].navdat[:,0]                # array to hold longitude
    lat = data["navdat"].navdat[:,1]                # array to hold latitude
    elev_air = data["navdat"].navdat[:,2]           # array to hold aircraft elevation
    twtt_surf = data["twtt_surf"]                   # array to hold twtt to surface below nadir position
    pick_idx = np.repeat(np.nan,lon.shape[0])       # array to hold indeces of picks
    twtt_bed = np.repeat(np.nan,lon.shape[0])       # array to hold twtt to pick indeces
    thick = np.repeat(np.nan,lon.shape[0])          # array to hold derived thickness from picks
    elev_gnd = np.repeat(np.nan,lon.shape[0])       # array to hold ground(surface) elevation
    elev_bed = np.repeat(np.nan,lon.shape[0])       # array to hold derived bed elevation from picks

    # iterate through pick_dict layers adding data to export arrays
    for _i in range(len(pick_dict)):
        picked_traces = np.where(pick_dict["segment_" + str(_i)] != -1)[0]

        pick_idx[picked_traces] = pick_dict["segment_" + str(_i)][picked_traces]

        twtt_bed[picked_traces] = pick_dict["segment_" + str(_i)][picked_traces]*data["dt"]    # convert pick idx to twtt

        # calculate ice thickness - using twtt_bed and twtt_surf
        thick[picked_traces] = ((((pick_dict["segment_" + str(_i)][picked_traces]*data["dt"]) - (data["twtt_surf"][picked_traces])) * v_ice) / 2)

    # calculate gnd elevation 
    elev_gnd = [a-(b*3e8/2) for a,b in zip(elev_air,twtt_surf)]

    # calculate bed elevation
    elev_bed = [a-b for a,b in zip(elev_air,thick)]

    # if twtt_surf not in data, replace values for twtt_surf, elev_gnd, elev_bed, and thick with NaN's to be recalculated later
    if not np.any(data["twtt_surf"]):
        twtt_surf = np.repeat(np.nan,lon.shape[0])
        thick = np.repeat(np.nan,lon.shape[0])
        elev_gnd = np.repeat(np.nan,lon.shape[0])
        elev_bed = np.repeat(np.nan,lon.shape[0])

    # combine the data into a matrix for export
    dstack = np.column_stack((trace,lon,lat,elev_air,elev_gnd,twtt_surf,pick_idx,twtt_bed,elev_bed,thick))

    header = "trace,lon,lat,elev_air,elev_gnd,twtt_surf,pick_idx,twtt_bed,elev_bed,thick"
    np.savetxt(f_saveName, dstack, delimiter=",", newline="\n", fmt="%s", header=header, comments="")
    print("Pick data exported: " + f_saveName)


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
    print("Pick image exported: " + fname.rstrip(".csv") + ".png")

# twtt2depth function
def twtt2depth(a, eps=3.15):
    v = 3e8/np.sqrt(eps)
    depth = a*v/(2*1000)           # convert input twtt to distance in km
    return depth

# depth2twtt function
def depth2twtt(a, eps=3.15):
    v = 3e8/np.sqrt(eps)
    twtt = a*2*1e3/v                # convert input depth to meters, then return twtt
    return twtt