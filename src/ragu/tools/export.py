# RAGU - Radar Analysis Graphical Utility
#
# copyright © 2020 btobers <tobers.brandon@gmail.com>
#
# distributed under terms of the GNU GPL3.0 license
"""
pick export functions for RAGU
"""
### imports ###
from ragu.tools import utils
from ragu.raguError import raguError
from ragu.tools.constants import *
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import tkinter as tk
import os, sys, h5py, fnmatch
import matplotlib.pyplot as plt

# pick_math is a function to perform all the necessary mathematics on a set of picks and save data as a pandas dataframe
# if overlapping pick segments exist, save as separate layers
def pick_math(rdata, i_eps_r=3.15, amp_out=True, horizon=None, srf=None):
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
        # get corresponding twtt - account for data truncation
        twtt_arr = np.repeat(np.nan, rdata.tnum)
        idx = ~np.isnan(samp_arr)
        twtt_arr[idx] = rdata.get_twtt()[samp_arr[idx].astype(int) +  rdata.truncs]
        out["twtt"] = twtt_arr
        # add in twtt_wind to get absolute twtt
        out["twtt"] += rdata.navdf["twtt_wind"]

        if type(damp) is np.ndarray:
            amp = np.repeat(np.nan, rdata.tnum)
            idx = ~np.isnan(samp_arr)
            amp[idx] = damp[samp_arr[idx].astype(int), idx]
            out["amp"] = amp
        return out

    ### export merged horizons ### - reference surface elevation if present
    if horizon is None:
        # iterate through interpretation horizons
        for i, (horizon, array) in enumerate(sample.items()):
            samp_arr = array + rdata.flags.sampzero
            out[horizon + "_sample"] = samp_arr
            # get corresponding twtt - account for data truncation
            twtt_arr = np.repeat(np.nan, rdata.tnum)
            idx = ~np.isnan(samp_arr)
            twtt_arr[idx] = rdata.get_twtt()[(samp_arr[idx].astype(int)) + rdata.truncs]
            out[horizon + "_twtt"] = twtt_arr
            # add in twtt_wind to get absolute twtt
            out[horizon + "_twtt"] += rdata.navdf["twtt_wind"]


            if horizon == srf:
                out[horizon + "_elev"] = rdata.get_srfElev()

            if type(damp) is np.ndarray:
                # export horizon amplitude values
                amp = np.repeat(np.nan, rdata.tnum)
                idx = ~np.isnan(samp_arr)
                # add any applied shift to index to pull proper sample amplitude from data array
                amp[idx] = damp[samp_arr[idx].astype(int), idx]
                out[horizon + "_amp"] = amp

            if i > 0:
                # get thickness between current layer and preceding layer
                # first confirm users preferred dielectric permittivity for layer
                eps_r = None
                while (eps_r is None) or (eps_r < 1):
                    eps_r = tk.simpledialog.askfloat("Dielectric Permittivity","Select a relative dielectric permittivity\nfor the unit between horizon <{}> and horizon <{}>".format(horizons[i - 1], horizons[i]), initialvalue=i_eps_r) 
                    if eps_r is None:
                        return None
                    elif eps_r < 1:
                        print("raguWarning: A relative dielectric permittivity >=1 must be specified in order to export picks")

                h = utils.twtt2depth(out[horizon + "_twtt"] - out[horizons[i - 1] + "_twtt"], rdata.asep, eps_r)
                # calculate layer bed elevation as elevation of preceding layer minus layer thickness - this only works if a surface with reference elevation is defined
                if srf:
                    out[horizon + "_elev"] = out[horizons[i - 1] + "_elev"] - h
                out[horizons[i - 1] + "_" + horizon + "_thick"] = h

        return out


# csv is a function to export the output pick dataframe as a csv
def csv(fpath, df):
    # fpath is the path for where the exported csv pick file should be saved [str]
    # df pick output dataframe
    if isinstance(df,pd.DataFrame):

        df.to_csv(fpath, index=False)

        print("csv picks exported successfully:\t" + fpath)


# gpkg is a funciton for saving picks to a geopackage/shapefile
def gpkg(fpath, df, crs):
    # fpath is the path for where the exported csv pick file should be saved [str]
    # df pick output dataframe
    # crs is the coordinate reference system for the shapefile output
    if isinstance(df,pd.DataFrame):
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


# dat is a method to export the radar data - for now just as a csv file array
def dat(fpath, dat):
    np.savetxt(fpath, dat, fmt="%s", delimiter=",")
    print("data exported successfully:\t" + fpath)


# log is a method to export the processing log as a python script
def log(fpath, log):
    with open(fpath,"w") as ofile:
        ofile.write("### RAGU processing log ###\nfrom ragu import ingest\n\n")
        for _i in log:
            ofile.write(_i + "\n")
        ofile.close()