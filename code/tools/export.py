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
import os, sys, h5py, fnmatch
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

    ### export single horizon ### - trace, lon, lat, elev, sample, twtt, amp
    if horizon and horizon in horizons:
        # apply sample time zero shift back in
        samp_arr = sample[horizon] + rdata.flags.sampzero
        out["sample"] = samp_arr
        out["twtt"] = utils.sample2twtt(samp_arr, rdata.dt)
        # for sharad, add in twtt_wind to get absolute twtt
        if rdata.dtype == "sharad":
            out["twtt"] += rdata.navdf["twtt_wind"]

        if type(damp) is np.ndarray:
            amp = np.repeat(np.nan, rdata.tnum)
            idx = ~np.isnan(samp_arr)
            amp[idx] = damp[samp_arr[idx].astype(np.int), idx]
            out["amp"] = amp
        return out

    ### export merged horizons ### - reference surface elevation if present
    if srf:
        # iterate through interpretation horizons
        for i, (horizon, array) in enumerate(sample.items()):
            samp_arr = array + rdata.flags.sampzero
            out[horizon + "_sample"] = samp_arr
            out[horizon + "_twtt"] = utils.sample2twtt(samp_arr, rdata.dt)
            # for sharad, add in twtt_wind to get absolute twtt
            if rdata.dtype == "sharad":
                out[horizon + "_twtt"] += rdata.navdf["twtt_wind"]

            if horizon == srf:
                # elev[horizon] = rdata.srfElev
                out[horizon + "_elev"] = rdata.get_srfElev()

                if type(damp) is np.ndarray:
                    # export horizon amplitude values
                    amp = np.repeat(np.nan, rdata.tnum)
                    idx = ~np.isnan(samp_arr)
                    # add any applied shift to index to pull proper sample amplitude from data array
                    amp[idx] = damp[samp_arr[idx].astype(np.int), idx]
                    out[srf + "_amp"] = amp
                continue

            # calculate cumulative layer thickness from srf
            h = (((out[horizon + "_twtt"] - out[srf + "_twtt"]) * v) / 2)

            # calculate layer bed elevation
            out[horizon + "_elev"] = out[srf + "_elev"] - h

            if type(damp) is np.ndarray:
                    # export horizon amplitude values
                    amp = np.repeat(np.nan, rdata.tnum)
                    idx = ~np.isnan(samp_arr)
                    # add any applied shift to index to pull proper sample amplitude from data array
                    amp[idx] = damp[samp_arr[idx].astype(np.int), idx]
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

    # if no surface horizon specified, don't reference surface elevation
    else:
        # iterate through interpretation horizons
        for i, (horizon, array) in enumerate(sample.items()):
            samp_arr = array + rdata.flags.sampzero
            out[horizon + "_sample"] = samp_arr
            out[horizon + "_twtt"] = utils.sample2twtt(samp_arr, rdata.dt)
            # for sharad, add in twtt_wind to get absolute twtt
            if rdata.dtype == "sharad":
                out[horizon + "_twtt"] += rdata.navdf["twtt_wind"]

            if type(damp) is np.ndarray:
                    # export horizon amplitude values
                    amp = np.repeat(np.nan, rdata.tnum)
                    idx = ~np.isnan(samp_arr)
                    # add any applied shift to index to pull proper sample amplitude from data array
                    amp[idx] = damp[samp_arr[idx].astype(np.int), idx]
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
    if df_copy["lon"].isnull().all() or df_copy["lat"].isnull().all():
        print("no geopackage was exported due to missing gps data")
        return
    # convert lon, lat to shapely points
    geometry = [Point(xy) for xy in zip(df_copy["lon"], df_copy["lat"])]
    df_copy.drop(["lon", "lat"], axis=1)

    # create geopandas df and export
    gdf = gpd.GeoDataFrame(df, crs=crs, geometry=geometry)
    gdf.to_file(fpath, driver="GPKG")

    print("geopackage exported successfully:\t" + fpath)


# h5 is a function for saving twtt_bed pick to h5 data file
def h5(fpath, df=None, dtype=None, srf=None):
    # fpath is the data file path [str]
    # df pick output dataframe
    if (dtype=="oibak"):
        f = h5py.File(fpath, "a")
        flag = False
        # update twtt_surf
        if srf:
            dat = df[srf + "_twtt"].to_numpy()
            # if twtt_surf exists in file, see it current picks have been modified
            if "twtt_surf" in f["drv"]["pick"].keys():
                twtt_srf_dfile = f["drv"]["pick"]["twtt_surf"][:]
                twtt_srf_dfile[twtt_srf_dfile == -1] = np.nan
                twtt_srf_dfile[twtt_srf_dfile == -9] = np.nan
                if not utils.nan_array_equal(twtt_srf_dfile, dat) or (np.isnan(twtt_srf_dfile).all()):
                    if (tk.messagebox.askyesno("twtt_surf","Export twtt_surf pick layer to data file?")):
                        del f["drv"]["pick"]["twtt_surf"]
                        flag = True
            elif (tk.messagebox.askyesno("twtt_surf","Export twtt_surf pick layer to data file?")):
                flag = True
            if flag:
                dat[np.isnan(dat)] = -9
                twtt_surf = f["drv"]["pick"].require_dataset("twtt_surf", data=dat, shape=dat.shape, dtype=np.float32)
                # twtt_surf.attrs.create("Unit", np.string_("Seconds"))
                # twtt_surf.attrs.create("Source", np.string_("Manual pick layer"))
                print("twtt_surf exported successfully:\t" + fpath + "/drv/pick/twtt_surf")

        # update twtt_bed
        if "bed_twtt" in df.keys():
            dat = df["bed_twtt"].to_numpy()
            dat[np.isnan(dat)] = -9
            if "twtt_bed" in f["drv"]["pick"].keys():
                if (f["drv"]["pick"]["twtt_bed"][:] == dat).all():
                    return
                elif tk.messagebox.askyesno("twtt_bed","Export twtt_bed pick layer to data file?"):
                    del f["drv"]["pick"]["twtt_bed"]
            elif not tk.messagebox.askyesno("twtt_bed","Export twtt_bed pick layer to data file?"):
                return
            twtt_bed = f["drv"]["pick"].require_dataset("twtt_bed", data=dat, shape=dat.shape, dtype=np.float32)
            # twtt_bed.attrs.create("Unit", np.string_("Seconds"))
            # twtt_bed.attrs.create("Source", np.string_("Manual pick layer"))
            print("twtt_bed exported successfully:\t\t" + fpath + "/drv/pick/twtt_bed")
        f.close()

    else:
        return


# fig is a function for exporting the pick image
def fig(fpath, fig):
    fig.savefig(fpath, dpi=500, bbox_inches='tight', pad_inches=0.05, transparent=True)# facecolor = "#d9d9d9")
    print("figure exported successfully:\t" + fpath)


# proc is a method to export the processed radar data - for now just as a csv file array
def proc(fpath, dat):
    # convert from dB to amp
    amp = utils.powdB2amp(dat)
    np.savetxt(fpath, amp, fmt="%s", delimiter=",")
    print("processed amplitude data exported successfully:\t" + fpath)


# log is a method to export the processing log as a python script
def log(fpath, log):
    with open(fpath,"w") as ofile:
        cdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ofile.write("### RAGU processing log ###\nimport sys\n# change dir to RAGU code directory\nsys.path.append('{}')\nfrom ingest import ingest\n\n".format(cdir))
        for _i in log:
            ofile.write(_i.replace("self.","") + "\n")
        ofile.close()