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

    # get list of horizon names
    horizons = list(rdata.pick.horizons.keys())

    # if horizon specified export unmerged interpretation
    if horizon and horizon in horizons:
        sample = rdata.pick.horizons[horizon]
        out["sample"] = sample
        twtt = utils.sample2twtt(sample, rdata.dt)
        out["twtt"] = twtt

        if damp is None:
            pass
        else:
            amp = np.repeat(np.nan, rdata.tnum)
            idx = ~np.isnan(sample)
            # add any applied shift to index to pull proper sample amplitude from data array
            amp[idx] = damp[(sample[idx].astype(np.int) + rdata.flags.sampzero) ,idx]
            out["amp"] = amp
        return out
    
    else:
        twtt = {}
        elev = {}
        amp = {}
        thick = {}   

        if srf:
            # iterate through interpretation horizons
            for i, (horizon, array) in enumerate(sample.items()):
                out[horizon + "_sample"] = sample[horizon]
                twtt[horizon] = utils.sample2twtt(array, rdata.dt)
                out[horizon + "_twtt"] = twtt[horizon]

                if horizon == srf: 
                    elev[horizon] = rdata.srfElev
                    out[horizon + "_elev"] = elev[horizon]

                    if type(damp) is np.ndarray:
                        # export horizon amplitude values
                        amp[horizon] = np.repeat(np.nan, rdata.tnum)
                        idx = ~np.isnan(sample[horizon])
                        # add any applied shift to index to pull proper sample amplitude from data array
                        amp[horizon][idx] = damp[(sample[horizon][idx].astype(np.int) + rdata.flags.sampzero) ,idx]
                        out[srf + "_amp"] = amp[horizon]
                    continue

                # calculate cumulative layer thickness from srf
                h = (((twtt[horizon] - twtt[srf]) * v) / 2)

                # calculate layer bed elevation
                elev[horizon] = elev[srf] - h
                out[horizon + "_elev"] = elev[horizon]

                if type(damp) is np.ndarray:
                        # export horizon amplitude values
                        amp[horizon] = np.repeat(np.nan, rdata.tnum)
                        idx = ~np.isnan(sample[horizon])
                        # add any applied shift to index to pull proper sample amplitude from data array
                        amp[horizon][idx] = damp[(sample[horizon][idx].astype(np.int) + rdata.flags.sampzero) ,idx]
                        out[srf + "_amp"] = amp[horizon]

                # if not 0th layer, reference bed elevation of upper layer for thickness
                if i == 1:
                    thick[horizon] = h
                elif i > 1:
                    # calculate layer thickness
                    thick[horizon] = elev[horizons[i - 1]] - elev[horizon]
                else:
                    continue
                out[horizons[i - 1] + "_" + horizon + "_thick"] = thick[horizon]

            return out

        # if no surface horizon specified, just output merged df with each horizon sample, twtt, amp
        else:
            # iterate through interpretation horizons
            for i, (horizon, array) in enumerate(sample.items()):
                out[horizon + "_sample"] = sample[horizon]
                twtt[horizon] = utils.sample2twtt(array, rdata.dt)
                out[horizon + "_twtt"] = twtt[horizon]

                if type(damp) is np.ndarray:
                        # export horizon amplitude values
                        amp[horizon] = np.repeat(np.nan, rdata.tnum)
                        idx = ~np.isnan(sample[horizon])
                        # add any applied shift to index to pull proper sample amplitude from data array
                        amp[horizon][idx] = damp[(sample[horizon][idx].astype(np.int) + rdata.flags.sampzero) ,idx]
                        out[srf + "_amp"] = amp[horizon]

                # calculate thickness between subsequent horizons
                if i >= 1:
                    # calculate layer thickness
                                    # calculate cumulative layer thickness from srf
                    out[horizons[i - 1] + "_" + horizon + "_thick"] = (((twtt[horizon] - twtt[horizons[i - 1]]) * v) / 2)
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


# fig is a function for exporting the pick image
def fig(fpath, fig, imtype = None):
    fig.savefig(fpath, dpi = 500, bbox_inches='tight', pad_inches = 0.05, transparent=True)# facecolor = "#d9d9d9")
    print(imtype + " figure exported successfully:\t" + fpath)


# proc is a method to export the processed radar data - for now just as a csv file array
def proc(fpath, dat):
    # convert from dB to amp
    amp = utils.powdB2amp(dat)
    np.savetxt(fpath, amp, fmt="%s", delimiter=",")

    print("processed amplitude data exported successfully:\t" + fpath)