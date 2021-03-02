# RAGU - Radar Analysis Graphical Utility
#
# copyright © 2020 btobers <tobers.brandon@gmail.com>
#
# distributed under terms of the GNU GPL3.0 license
"""
nav library contains various fucntions for reading radar nav data and transforming crs
"""
### imports ###
from nav.gps import GPSdat
from tools.constants import *
import sys,os
import pandas as pd
import rasterio as rio
from rasterio.plot import show
import numpy as np
import scipy.io as scio
import pyproj, h5py, codecs
import matplotlib.pyplot as plt

# various getnav functions must return a pandas dataframe consisting of the following cols -
# ["lon", "lat", "elev", "x", "y", "z", "dist"], where xyz are planetocentric radar platform location
# and dist is along track distance in meters

# geocentric crd dict
xyzsys = {
"mars": "+proj=geocent +a=3396190 +b=3376200 +no_defs",
"earth": "+proj=geocent +a=6378140 +b=6356750 +no_defs",
}

def getnav_oibAK_h5(navfile, navcrs, body):
    h5 = h5py.File(navfile, "r")
    if "nav0" in h5["ext"].keys():
        nav = h5["ext"]["nav0"][:]
        df = pd.DataFrame(nav)
        try:
            df.rename(columns={"hgt": "elev"}, inplace=True)
        except:
            pass
        try:
            df.rename(columns={"altM": "elev"}, inplace=True)
        except Exception as err:
            print("getnav_oibAK_h5 error: " + str(err))
    
    elif "loc0" in h5["raw"].keys():
        nav = h5["raw"]["loc0"][:]
        df = pd.DataFrame(nav)
        # Interpolate non-unique values
        hsh = nav["lat"] + nav["lon"] * 1e4
        idx = np.arange(0, len(hsh), 1)
        uniq, uidx = np.unique(hsh, return_index=True)
        uidx = np.sort(uidx)
        uidx[-1] = len(hsh) - 1  # Handle end of array
        df["lat"] = np.interp(idx, uidx, df["lat"][uidx])
        df["lon"] = np.interp(idx, uidx, df["lon"][uidx])
        df["elev"] = np.interp(idx, uidx, df["hgt"][uidx])

    else:
        h5.close()
        print("No valid navigation data found in file %s" % navfile)
        sys.exit()

    h5.close()

    df["x"], df["y"], df["z"] = pyproj.transform(
        navcrs,
        xyzsys[body],
        df["lon"].to_numpy(),
        df["lat"].to_numpy(),
        df["elev"].to_numpy(),
    )

    df["dist"] = euclid_dist(
        df["x"].to_numpy(),
        df["y"].to_numpy(),
        df["z"].to_numpy())

    return df[["lon", "lat", "elev", "x", "y", "z", "dist"]]


def getnav_oibAK_mat(navfile, navcrs, body):
    try:
        f = h5py.File(navfile, "r")
        lon = f["block"]["lon"].flatten()
        lat = f["block"]["lat"].flatten()
        elev = f["block"]["elev_air"].flatten()     
        f.close()
    except:
        try:
            f = scio.loadmat(navfile)
            lon = f["block"]["lon"][0][0].flatten()
            lat = f["block"]["lat"][0][0].flatten()
            elev = f["block"]["elev_air"][0][0].flatten() 
        except Exception as err:
            print("getnav_oibAK_mat Error: " + str(err))
            exit(1)

    df = pd.DataFrame({"lon": lon, "lat": lat, "elev": elev,
                                "x": np.nan, "z": np.nan, "z": np.nan,
                                "dist": np.nan})

    df["x"], df["y"], df["z"] = pyproj.transform(
        navcrs,
        xyzsys[body],
        df["lon"].to_numpy(),
        df["lat"].to_numpy(),
        df["elev"].to_numpy(),
    )

    df["dist"] = euclid_dist(
        df["x"].to_numpy(),
        df["y"].to_numpy(),
        df["z"].to_numpy())

    return df[["lon", "lat", "elev", "x", "y", "z", "dist"]]


def getnav_gssi(navfile, tnum, navcrs, body):
    if os.path.isfile(navfile):
        with codecs.open(navfile, "r", encoding="utf-8", errors="ignore") as f_in:
            lines = f_in.readlines()
        # We have to be careful with this to permit other NMEA strings to have been recorded
        # and to be sure that the indices line up
        gssis_inds = [i for i, line in enumerate(lines) if "GSSIS" in line]
        gga_inds = [i for i, line in enumerate(lines) if "GGA" in line]
        # we may have some records without GGA, so check if this is the case;
        # we keep track of the offset if so
        gssis_inds_keep = []
        offset_ind = 0
        for i, j in enumerate(gssis_inds[:-1]):
            if (gga_inds[i + offset_ind] > j and gga_inds[i + offset_ind] < gssis_inds[i + 1]):
                gssis_inds_keep.append(j)
            else:
                offset_ind -= 1
        if gga_inds[-1] > gssis_inds[-1]:
            gssis_inds_keep.append(gssis_inds[-1])

        scans = np.array(list(map(lambda x: int(x.split(",")[1]),
                                [line for i, line in enumerate(lines) if i in gssis_inds_keep])))
        gps = GPSdat([line for i, line in enumerate(lines) if i in gga_inds], scans, tnum)
        df = pd.DataFrame({"lon": gps.lon, "lat": gps.lat, "elev": gps.elev,
                                    "x": np.nan, "y": np.nan, "z": np.nan,
                                    "dist": np.nan})

        df["x"], df["y"], df["z"] = pyproj.transform(
            navcrs,
            xyzsys[body],
            df["lon"].to_numpy(),
            df["lat"].to_numpy(),
            df["elev"].to_numpy(),
        )

        df["dist"] = euclid_dist(
            df["x"].to_numpy(),
            df["y"].to_numpy(),
            df["z"].to_numpy())
    else:
        nd = np.repeat(np.nan, tnum)
        df = pd.DataFrame({"lon": nd, "lat": nd, "elev": nd,
                                    "x": nd, "y": nd, "z": nd,
                                    "dist": nd})

    return df[["lon", "lat", "elev", "x", "y", "z", "dist"]]


def getnav_pulseekko(navfile, tnum, navcrs, body):
    """
    read GPS data associated with a pulseEkko .GPS file
    adapted from ImpDAR/lib/load/load_pulse_ekko._get_gps_data - David Lilien

    """
    if os.path.isfile(navfile):
        try:
            with open(navfile) as f_in:
                lines = f_in.readlines()
            ggis = []
            gga = []
            for line in lines:
                if line[:5] == "Trace":
                    ggis.append(line)
                elif line[:6] == "$GPGGA":
                    gga.append(line)
                else:
                    continue
            if len(gga) == 0:
                raise ValueError("Can currently only work with gga strings")
            # scans = np.array(list(map(lambda x: int(float(
            #     x.rstrip("\n\r ").split(" ")[-1])), ggis)))
            # i believe that this is what we want for scans, with the actual trace number for each scan
            scans = np.array(list(map(lambda x: int(float(
                x.rstrip("\n\r ").split(" ")[1][1:])), ggis))) - 1

            gps = GPSdat([line for line in lines if line in gga], scans, tnum)
            df = pd.DataFrame({"lon": gps.lon, "lat": gps.lat, "elev": gps.elev,
                                        "x": np.nan, "y": np.nan, "z": np.nan,
                                        "dist": np.nan})

            df["x"], df["y"], df["z"] = pyproj.transform(
                navcrs,
                xyzsys[body],
                df["lon"].to_numpy(),
                df["lat"].to_numpy(),
                df["elev"].to_numpy(),
            )

            df["dist"] = euclid_dist(
                df["x"].to_numpy(),
                df["y"].to_numpy(),
                df["z"].to_numpy())

        except Exception as err:
            print("getnav_pulsekko error: " + str(err))
            nd = np.repeat(np.nan, tnum)
            df = pd.DataFrame({"lon": nd, "lat": nd, "elev": nd,
                                        "x": nd, "y": nd, "z": nd,
                                        "dist": nd})

    else:
        nd = np.repeat(np.nan, tnum)
        df = pd.DataFrame({"lon": nd, "lat": nd, "elev": nd,
                                    "x": nd, "y": nd, "z": nd,
                                    "dist": nd})

    return df[["lon", "lat", "elev", "x", "y", "z", "dist"]]

    
def getnav_sharad(navfile, navcrs, body):
    geomCols = [
        "trace",
        "time",
        "lat",
        "lon",
        "marsRad",
        "scRad",
        "radiVel",
        "tangVel",
        "SZA",
        "phaseD",
    ]
    df = pd.read_csv(navfile, names=geomCols, index_col=False)

    # Planetocentric lon,lat,radius to x,y,z
    df["x"] = (
        (df["scRad"] * 1000)
        * np.cos(np.radians(df["lat"]))
        * np.cos(np.radians(df["lon"]))
    )
    df["y"] = (
        (df["scRad"] * 1000)
        * np.cos(np.radians(df["lat"]))
        * np.sin(np.radians(df["lon"]))
    )
    df["z"] = (df["scRad"] * 1000) * np.sin(np.radians(df["lat"]))

    df["dist"] = euclid_dist(
        df["x"].to_numpy(),
        df["y"].to_numpy(),
        df["z"].to_numpy())

    # SHARAD FPB sample 1800 corresponds to the areoid height - use areoid to reference SC elevation and get absolute twtt
    aerPath = os.path.split(os.getcwd())[0] + "/dat/mars/mega90n000eb.tif"
    try:
        aer = rio.open(aerPath, mode="r")

    except:
        print("Unable to open areoid file. Is it located at : " + aerPath + " ?")
        sys.exit(1)

    # transform MRO lon/lat to areoid x/y to sample areoid radius along SC path 
    aerX, aerY = pyproj.transform(
        navcrs, aer.crs, df["lon"].to_numpy(), df["lat"].to_numpy()
    )

    # get raster x/y index of SC x/y positions
    ix,iy = aer.index(aerX,aerY)
    aerZ = aer.read(1)[ix,iy]

    # use elevation above areiod as radar elevation  = scRad - (3396000 + rAreoid) - (2*1800*dt/c)
    df["elev"] = (1000.0*df["scRad"]) - 3396000.0 - aerZ - (2*1800*37.5e-9/C)

    # get twtt for SHARAD opening receive window from SC to top of radargram = 2*(scRad - evel_samp0)/c
    # this will be added back in upon export to get absolute twtt of picks
    df["twtt_wind"] = 2*(df["scRad"] - df["elev"])/C

    return df[["lon", "lat", "elev", "x", "y", "z","twtt_wind", "dist"]]


def getnav_marsis(navfile, navcrs, body):
    geomCols = [
        "trace",
        "ephemerisTime",
        "time",
        "lat",
        "lon",
        "elev",
        "sza",
        "ch0",
        "ch1",
        "x",
        "y",
        "z",
        "radiVel",
        "tangVel",
    ]
    df = pd.read_csv(navfile, names=geomCols, index_col=False)

    df["x"] = df["x"]*1000
    df["y"] = df["y"]*1000
    df["z"] = df["z"]*1000
    
    df["dist"] = euclid_dist(
        df["x"].to_numpy(),
        df["y"].to_numpy(),
        df["z"].to_numpy())

    return df[["lon", "lat", "elev", "x", "y", "z", "dist"]]


def euclid_dist(xarray, yarray,zarray):
    dist = np.zeros_like(xarray)
    dist[1:] = np.cumsum(np.sqrt(np.diff(xarray) ** 2.0 + np.diff(yarray) ** 2.0 + np.diff(zarray) ** 2.0))
    return dist