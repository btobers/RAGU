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
def pick_math(rdata, eps_r, amp_out = True):
    v = C/(np.sqrt(eps_r))                      # wave veloity

    trace = np.arange(rdata.tnum)               # array to hold trace number
    lon = rdata.navdf["lon"]                    # array to hold longitude
    lat = rdata.navdf["lat"]                    # array to hold latitude
    alt = rdata.navdf["elev"]                   # array to hold aircraft elevation
    gndElev = rdata.gndElev                     # array to hold ground elevation
    subsurf_pk = np.repeat(np.nan, rdata.tnum)  # array to hold indeces of subsurface picks

    # if existing surface pick, and no current -> use existing
    if np.isnan(rdata.pick.current_surf).all() and not np.isnan(rdata.pick.existing_twttSurf).all():
        srfTwtt = rdata.pick.existing_twttSurf
        srf = utils.twtt2sample(srfTwtt, rdata.dt)

    else:
        srf = rdata.pick.current_surf
        srfTwtt = utils.sample2twtt(srf, rdata.dt)

    # iterate through pick segments adding data to export arrays
    for _i in rdata.pick.current_subsurf.keys():
        picked_traces = np.where(~np.isnan(rdata.pick.current_subsurf[str(_i)]))[0]

        subsurf_pk[picked_traces] = rdata.pick.current_subsurf[str(_i)][picked_traces]

    # convert pick sample to twtt
    subsrfTwtt = utils.sample2twtt(subsurf_pk, rdata.dt)

    # calculate ice thickness
    thick = (((subsrfTwtt - srfTwtt) * v) / 2)

    # calculate bed elevation
    subsrfElev = gndElev - thick

    if (amp_out) and (rdata.dtype != "marsis"):

        # if raw data is complex, take absolute value to get amplitude
        if np.iscomplex(rdata.dat).all():
            amp = np.abs(rdata.dat)
        elif np.iscomplexobj(rdata.dat):
            amp = np.real(rdata.dat)
        else:
            amp = rdata.dat

        # export surface and subsurface pick amplitude values
        srfAmp = np.repeat(np.nan, rdata.tnum)
        idx = ~np.isnan(srf)
        # add any applied shift to index to pull proper sample amplitude from data array
        srfAmp[idx] = amp[(srf[idx].astype(np.int) + rdata.flags.sampzero) ,idx]

        subsrfAmp = np.repeat(np.nan, rdata.tnum)
        idx = ~np.isnan(subsurf_pk)
        # add any applied shift to index to pull proper sample amplitude from data array
        subsrfAmp[idx] = amp[(subsurf_pk[idx].astype(np.int) + rdata.flags.sampzero), idx]
        
        out = pd.DataFrame({"trace": trace, "lon": lon, "lat": lat, "alt": alt, "gndElev": gndElev,
                            "srfIdx": srf, "srfTwtt": srfTwtt, "srfAmp": srfAmp, 
                            "subsrfIdx": subsurf_pk, "subsrfTwtt": subsrfTwtt, 
                            "subsrfAmp": subsrfAmp, "subsrfElev": subsrfElev, "thick": thick})

    else:
        out = pd.DataFrame({"trace": trace, "lon": lon, "lat": lat, "alt": alt, "gndElev": gndElev,
                            "srfIdx": srf, "srfTwtt": srfTwtt, "srfAmp": np.nan, 
                            "subsrfIdx": subsurf_pk, "subsrfTwtt": subsrfTwtt, 
                            "subsrfAmp": np.nan, "subsrfElev": subsrfElev, "thick": thick})

    # remove alt if ground-based data and update header
    if utils.nan_array_equal(alt, gndElev):
        out = out.drop(columns=["alt"])
        out = out.rename(columns={"gndElev": "elev"})

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


# h5 is a function for saving twtt_ssrf pick to h5 data file
def h5(fpath, df):
    # fpath is the data file path [str]
    # df pick output dataframe
    dat = df["subsrfTwtt"].to_numpy()

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