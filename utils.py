import ingester
import numpy as np
from tkinter import filedialog, messagebox
import matplotlib.pyplot as plt
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
def savePick(f_saveName, data, pick_dict):
    f_saveName = f_saveName
    data = data
    pick_dict = pick_dict

    v_ice = 3e8/np.sqrt(3.15)   # EM wave veloity in ice - for thickness calculation
    # vars to hold info from pick locations
    lon = []
    lat = []
    elev_air = []
    twtt_surf = []
    twtt_bed = []
    thick = []
    # get necessary data from radargram for pick locations
    # iterate through pick_dict layers
    for _i in range(len(pick_dict)):
        pick_idx = np.where(pick_dict["layer_" + str(_i)] != -1)[0]

        lon.append(data["navdat"].navdat[pick_idx[:],0])
        lat.append(data["navdat"].navdat[pick_idx[:],1])
        elev_air.append(data["navdat"].navdat[pick_idx[:],2])
        twtt_surf.append(data["twtt_surf"][pick_idx[:]])
        twtt_bed.append(pick_dict["layer_" + str(_i)][pick_idx[:]])

        # calculate ice thickness - using twtt_bed and twtt_surf
        thick.append((((pick_dict["layer_" + str(_i)][pick_idx] * 1e-6) - (data["twtt_surf"][pick_idx]* 1e-6)) * v_ice) / 2)
        
    # combine the data into a matrix for export
    dstack = np.column_stack((np.hstack(lon).T,np.hstack(lat).T,np.hstack(elev_air).T,np.hstack(twtt_surf).T,np.hstack(twtt_bed).T,np.hstack(thick).T))

    header = "lon,lat,elev_air,twtt_surf,twtt_bed,thick"
    np.savetxt(f_saveName, dstack, delimiter=",", newline="\n", fmt="%.8f", header=header, comments="")
    print("Picks exported: ", f_saveName)


def find_nearest(array,value):
    # return index in array with value closest to the passed value
    idx = (np.abs(array-value)).argmin()
    return idx