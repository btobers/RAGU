# RAGU - Radar Analysis Graphical Utility
#
# copyright © 2020 btobers <tobers.brandon@gmail.com>
#
# distributed under terms of the GNU GPL3.0 license
"""
pick export functions for RAGU
"""
### imports ###
from tools import utils
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import tkinter as tk
import sys, h5py, fnmatch
from tools.constants import *
import matplotlib.pyplot as plt

# pick_math is a function to perform all the necessary mathematics on a set of picks and save data as a pandas dataframe
# if overlapping pick segments exist, save as separate layers
def pick_math(rdata, eps_r, amp_out = True):
    v = C/(np.sqrt(eps_r))                              # wave veloity
    trace = np.arange(rdata.tnum)                       # array to hold trace number
    picked_traces = {}
    subsurf_idx = {}          
    subsurfTwtt = {} 
    thick = {}          
    subsurfelev = {}
    subsurfAmp = {}
    lyr = 0
    
    # if existing surface pick, and no current -> use existing
    if np.isnan(rdata.pick.current_surf).all() and not np.isnan(rdata.pick.existing_twttSurf).all():
        surfTwtt = rdata.pick.existing_twttSurf
        surf_idx = utils.twtt2sample(surfTwtt, rdata.dt)

    # else if the user created surface pick use that surface
    else:
        surf_idx = rdata.pick.current_surf
        surfTwtt = utils.sample2twtt(surf, rdata.dt)

    # iterate through pick segments adding data to export array
    for key, arr in rdata.pick.current_subsurf.items():
        picked_traces[key] = np.where(~np.isnan(arr))[0]
        # if segment overlaps previous segment, create new dict layer to hold pick
        if (key > 0) and (np.intersect1d(picked_traces[key], picked_traces[key - 1]).shape[0] > 0):
            lyr += 1
        
        if lyr not in subsurf_idx:
            subsurf_idx[lyr] = np.repeat(np.nan, rdata.tnum)
            subsurf_idx[lyr][picked_traces[key]] = arr[picked_traces[key]]

    # iterate through total number of subsurface pick layers
    for key, arr in subsurf_idx.items():
        # convert pick sample to twtt
        subsurfTwtt[key] = utils.sample2twtt(arr, rdata.dt)

        # calculate cumulative thickness
        h = (((subsurfTwtt[key] - surfTwtt) * v) / 2)

        # calculate layer bed elevation
        subsurfelev[key] = rdata.surfElev - h

        # if not 0th layer, reference above layer for thickness
        if key > 0:
            # calculate layer thickness
            thick[key] = subsurfelev[key - 1] - subsurfelev[key]
        else:
            thick[key] = h

    # initilize output dataframe
    out = pd.DataFrame({"trace": trace, 
                    "lon": rdata.navdf["lon"], 
                    "lat": rdata.navdf["lat"], 
                    "radelev": rdata.navdf["elev"], 
                    "surfElev": rdata.surfElev,
                    "surfIdx": surf_idx, 
                    "surfTwtt": surfTwtt})

    # get amplitude values for picks
    if (amp_out) and (rdata.dtype != "marsis"):

        # if raw data is complex, take absolute value to get amplitude
        if np.iscomplex(rdata.dat).all():
            amp = np.abs(rdata.dat)
        elif np.iscomplexobj(rdata.dat):
            amp = np.real(rdata.dat)
        else:
            amp = rdata.dat

        # export surface and subsurface pick amplitude values
        surfAmp = np.repeat(np.nan, rdata.tnum)
        idx = ~np.isnan(surf_idx)
        # add any applied shift to index to pull proper sample amplitude from data array
        surfAmp[idx] = amp[(surf_idx[idx].astype(np.int) + rdata.flags.sampzero) ,idx]

        out["surfAmp"] = surfAmp

        for key, arr in subsurf_idx.items():
            subsurfAmp[key] = np.repeat(np.nan, rdata.tnum)
            idx = ~np.isnan(arr)
            # add any applied shift to index to pull proper sample amplitude from data array
            subsurfAmp[key][idx] = amp[(arr[idx].astype(np.int) + rdata.flags.sampzero), idx]

            # add to output dataframe
            out["lyr" + str(key) + "Idx"] = arr
            out["lyr" + str(key) + "Twtt"] = subsurfTwtt[key]
            out["lyr" + str(key) + "elev"] = subsurfelev[key]
            out["lyr" + str(key) + "Thick"] = thick[key]
            out["lyr" + str(key) + "Amp"] = subsurfAmp[key]

    else:
        out["surfAmp"] = np.nan
        for key, arr in subsurf_idx.items():
            # add to output dataframe
            out["lyr" + str(key) + "Idx"] = arr
            out["lyr" + str(key) + "Twtt"] = subsurfTwtt[key]
            out["lyr" + str(key) + "elev"] = subsurfelev[key]
            out["lyr" + str(key) + "Thick"] = thick[key]
            out["lyr" + str(key) + "Amp"] = np.nan


    # remove alt if ground-based data and update header
    if utils.nan_array_equal(rdata.navdf["elev"], rdata.surfElev):
        out = out.drop(columns=["elev"])
        out = out.rename(columns={"surfElev": "elev"})

    return out


# csv is a function to export the output pick dataframe as a csv
def csv(fpath, df):
    # fpath is the path for where the exported csv pick file should be saved [str]
    # df pick output dataframe
    df.to_csv(fpath, index=False)

    print("csv picks exported successfully:\t" + fpath)


# gpkg is a funciton for saving picks to a geopackage/shapefile
def gpkg(fpath, df, crs):
    # fpath is the path for where the exported csv pick file should be saved [str]
    # df pick output dataframe
    # crs is the coordinate reference system for the shapefile output
    df_copy = df.copy()
    # convert lon, lat to shapely points
    geometry = [Point(xy) for xy in zip(df_copy["lon"], df_copy["lat"])]
    df_copy.drop(["lon", "lat"], axis=1)

    # create geopandas df and export
    gdf = gpd.GeoDataFrame(df, crs=crs, geometry=geometry)
    gdf.to_file(fpath, driver="GPKG")

    print("geopackage exported successfully:\t" + fpath)


# h5 is a function for saving twtt_ssurf pick to h5 data file
def h5(fpath, df):
    # fpath is the data file path [str]
    # df pick output dataframe
    dat = df["subsurfTwtt"].to_numpy()

    f = h5py.File(fpath, "a") 
    num_file_pick_lyr = len(fnmatch.filter(f["drv"]["pick"].keys(), "twtt_subsurf*"))
    # save the new subsurface pick to the hdf5 file - determine whther to overwrite or append
    if (num_file_pick_lyr > 0) and (tk.messagebox.askyesno("overwrite picks","overwrite most recent subsurface picks previously exported to data file (no to append as new subsurface pick layer)?") == True):
        del f["drv"]["pick"]["twtt_subsurf" + str(num_file_pick_lyr - 1)]
        twtt_subsurf_pick = f["drv"]["pick"].require_dataset("twtt_subsurf" + str(num_file_pick_lyr - 1), data=dat, shape=dat.shape, dtype=np.float32)
    else:
        twtt_subsurf_pick = f["drv"]["pick"].require_dataset("twtt_subsurf" + str(num_file_pick_lyr), data=dat, shape=dat.shape, dtype=np.float32)

    twtt_subsurf_pick.attrs.create("Unit", np.string_("Seconds"))
    twtt_subsurf_pick.attrs.create("Source", np.string_("Manual pick layer"))
    f.close()


# im is a function for exporting the pick image
def im(fpath, fig, imtype = None):
    fig.savefig(fpath, dpi = 500, bbox_inches='tight', pad_inches = 0.05, transparent=True)# facecolor = "#d9d9d9")
    print(imtype + " figure exported successfully:\t" + fpath)


# proc is a method to export the processed radar data - for now just as a csv file array
def proc(fpath, dat):
    # convert from dB to amp
    amp = utils.powdB2amp(dat)
    np.savetxt(fpath, amp, fmt="%s", delimiter=",")

    print("processed amplitude data exported successfully:\t" + fpath)