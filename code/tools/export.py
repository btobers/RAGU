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
def pick_math(rdata, eps_r=3.15, amp_out=True, horizon=None, srf=None):
    v = C/(np.sqrt(eps_r))                              # wave veloity
    trace = np.arange(rdata.tnum)                       # array to hold trace number
    sample = rdata.pick.horizons.copy()
    # get list of horizon names
    horizons = list(rdata.pick.horizons.keys())
    damp = None

    # prep data amplitude array
    if (amp_out) and (rdata.dtype != "marsis"):
        # if raw data is complex, take absolute value to get amplitude
        if np.iscomplex(rdata.dat).all():
            damp = np.abs(rdata.dat)
        elif np.iscomplexobj(rdata.dat):
            damp = np.real(rdata.dat)
        else:
            damp = rdata.dat

    # initilize output dataframe
    out = pd.DataFrame({"trace": trace, 
                    "lon": rdata.navdf["lon"], 
                    "lat": rdata.navdf["lat"], 
                    "elev": rdata.navdf["elev"]})

    # if horizon specified export unmerged interpretation
    if horizon and horizon in horizons:
        sample = sample[horizon]
        out["sample"] = sample
        twtt = utils.sample2twtt(sample, rdata.dt)
        out["twtt"] = twtt

        if damp is None:
            pass
        else:
            amp = np.repeat(np.nan, rdata.tnum)
            idx = ~np.isnan(sample)
            # add any applied shift to index to pull proper sample amplitude from data array
            amp[idx] = damp[(sample[idx].astype(np.int) + rdata.flags.sampzero), idx]
            out["amp"] = amp
        return out
    
    if srf:
        # iterate through interpretation horizons
        for i, (horizon, array) in enumerate(sample.items()):
            out[horizon + "_sample"] = array
            out[horizon + "_twtt"] = utils.sample2twtt(array, rdata.dt)

            if horizon == srf: 
                # elev[horizon] = rdata.srfElev
                out[horizon + "_elev"] = rdata.srfElev

                if type(damp) is np.ndarray:
                    # export horizon amplitude values
                    amp = np.repeat(np.nan, rdata.tnum)
                    idx = ~np.isnan(array)
                    # add any applied shift to index to pull proper sample amplitude from data array
                    amp[idx] = damp[(array[idx].astype(np.int) + rdata.flags.sampzero), idx]
                    out[srf + "_amp"] = amp
                continue

            # calculate cumulative layer thickness from srf
            h = (((out[horizon + "_twtt"] - out[srf + "_twtt"]) * v) / 2)

            # calculate layer bed elevation
            out[horizon + "_elev"] = out[srf + "_elev"] - h

            if type(damp) is np.ndarray:
                    # export horizon amplitude values
                    amp = np.repeat(np.nan, rdata.tnum)
                    idx = ~np.isnan(array)
                    # add any applied shift to index to pull proper sample amplitude from data array
                    amp[idx] = damp[(array[idx].astype(np.int) + rdata.flags.sampzero), idx]
                    out[horizon + "_amp"] = amp

            # if not 0th layer, reference bed elevation of upper layer for thickness
            if i == 1:
                thick = h
            elif i > 1:
                # calculate layer thickness
                thick = out[horizons[i - 1] + "_elev"] - out[horizon + "_elev"]
            else:
                continue
            out[horizons[i - 1] + "_" + horizon + "_thick"] = thick

        return out

    # if no surface horizon specified, output merged df with each horizon sample, twtt, amp
    else:
        # iterate through interpretation horizons
        for i, (horizon, array) in enumerate(sample.items()):
            out[horizon + "_sample"] = array
            out[horizon + "_twtt"] = utils.sample2twtt(array, rdata.dt)

            if type(damp) is np.ndarray:
                    # export horizon amplitude values
                    amp = np.repeat(np.nan, rdata.tnum)
                    idx = ~np.isnan(array)
                    # add any applied shift to index to pull proper sample amplitude from data array
                    amp[idx] = damp[(array[idx].astype(np.int) + rdata.flags.sampzero), idx]
                    out[horizon + "_amp"] = amp

            # calculate thickness between subsequent horizons
            if i >= 1:
                # calculate layer thickness
                out[horizons[i - 1] + "_" + horizon + "_thick"] = (((out[horizon + "_twtt"] - out[horizons[i - 1] + "_twtt"]) * v) / 2)
            else:
                continue

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


# h5 is a function for saving twtt_bed pick to h5 data file
def h5(fpath, df=None, dtype=None):
    # fpath is the data file path [str]
    # df pick output dataframe
    if dtype=="oibak":
        if not (tk.messagebox.askyesno("Update Picks","Update twtt_bed pick layer saved to data file?")):
            return
        dat = df["bed_twtt"]
        f = h5py.File(fpath, "a")
        # replace np.nan values in pick layer with -9
        dat[np.isnan(dat)] = -9

        if "twtt_bed" in f["drv"]["pick"].keys():
            del f["drv"]["pick"]["twtt_bed"]

        twtt_bed = f["drv"]["pick"].require_dataset("twtt_bed", data=dat, shape=dat.shape, dtype=np.float32)
        twtt_subsurf_pick.attrs.create("Unit", np.string_("Seconds"))
        twtt_subsurf_pick.attrs.create("Source", np.string_("Manual pick layer"))
        f.close()
        print("hdf5 pick layer exported successfully:\t" + fpath)
    else:
        return


# fig is a function for exporting the pick image
def fig(fpath, fig, imtype=None):
    fig.savefig(fpath, dpi=500, bbox_inches='tight', pad_inches=0.05, transparent=True)# facecolor = "#d9d9d9")
    print(imtype + " figure exported successfully:\t" + fpath)


# proc is a method to export the processed radar data - for now just as a csv file array
def proc(fpath, dat):
    # convert from dB to amp
    amp = utils.powdB2amp(dat)
    np.savetxt(fpath, amp, fmt="%s", delimiter=",")
    print("processed amplitude data exported successfully:\t" + fpath)