# RAGU - Radar Analysis Graphical Utility
#
# copyright © 2020 btobers <tobers.brandon@gmail.com>
#
# distributed under terms of the GNU GPL3.0 license
"""
nav library contains various fucntions for reading radar nav data and transforming crs
"""
### imports ###
from ragu.raguError import raguError
from ragu.nav.gps import GPSdat
from ragu.tools.constants import *
import sys,os
import pandas as pd
import rasterio as rio
from rasterio.plot import show
import numpy as np
import scipy.io as scio
import h5py, codecs
from pyproj import Transformer
import matplotlib.pyplot as plt

# various getnav functions must return a pandas dataframe consisting of the following cols -
# ["lon", "lat", "elev", "x", "y", "z", "twtt_wind", "dist"], where xyz are planetocentric radar platform location,
# dist is along track distance in meters, and twtt_wind is the twtt between radar platform and sample 0

# geocentric crs dict
xyzsys = {
"mars": "+proj=geocent +a=3396190 +b=3376200 +no_defs",
"earth": "+proj=geocent +a=6378140 +b=6356750 +no_defs",
"moon": "+proj=geocent +a=1737400 +b=1737400 +no_defs",
}


def get_xformer(crs_from, crs_to):
    return Transformer.from_crs(crs_from=crs_from, crs_to=crs_to)


def interp_xords(df, keys=["lon","lat","elev"]):
    # interpolate nans
    for key in keys:
        if key not in list(df.keys()):
            continue
        nan_indices = np.isnan(df[key].values)
        non_nan_indices = ~nan_indices
        non_nan_values = df[key].values[non_nan_indices]
        indices = np.arange(len(df[key]))
        # Interpolate NaN values
        df[key].values[nan_indices] = np.interp(indices[nan_indices], indices[non_nan_indices], non_nan_values)
    return df


def euclid_dist(xarray, yarray, zarray):
    dist = np.zeros_like(xarray)
    dist[1:] = np.cumsum(np.sqrt(np.diff(xarray) ** 2.0 + np.diff(yarray) ** 2.0 + np.diff(zarray) ** 2.0))
    return dist


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

    # transform to projected xords 
    xformer = get_xformer(navcrs, xyzsys[body])
    df["x"], df["y"], df["z"] = xformer.transform(
        df["lon"].to_numpy(),
        df["lat"].to_numpy(),
        df["elev"].to_numpy(),
    )

    df["dist"] = euclid_dist(
        df["x"].to_numpy(),
        df["y"].to_numpy(),
        df["z"].to_numpy())

    df["twtt_wind"] = 0.0

    return df[["lon", "lat", "elev", "x", "y", "z", "twtt_wind", "dist"]]


def getnav_groundhog(navfile, navcrs, body):
    h5 = h5py.File(navfile, "r")
    # get xord 
    xformer = get_xformer(navcrs, xyzsys[body])
    # use average of RX and TX gps positioning
    # we'll also record the separation distance between rx and tx per trace
    # get appropriate data grou
    grps = h5.keys()
    if "proc" in grps:
        grp = "proc"
    elif "restack" in grps:
        grp = "restack"
    else: 
        grp = "raw"

    k = h5[grp].keys()
    if ("txFix0" in k) and ("rxFix0" in k):
        nav_rx = pd.DataFrame(h5[grp]["rxFix0"][:])
        nav_tx = pd.DataFrame(h5[grp]["txFix0"][:])

        # Interpolate non-unique nav values in tx and rx datasets
        hsh = nav_rx["lat"] + nav_rx["lon"] * 1e4
        idx = np.arange(0, len(hsh), 1)
        uniq, uidx = np.unique(hsh, return_index=True)
        uidx = np.sort(uidx)
        uidx[-1] = len(hsh) - 1  # Handle end of array
        nav_rx["lat"] = np.interp(idx, uidx, nav_rx["lat"][uidx])
        nav_rx["lon"] = np.interp(idx, uidx, nav_rx["lon"][uidx])
        nav_rx["hgt"] = np.interp(idx, uidx, nav_rx["hgt"][uidx])

        hsh = nav_tx["lat"] + nav_tx["lon"] * 1e4
        idx = np.arange(0, len(hsh), 1)
        uniq, uidx = np.unique(hsh, return_index=True)
        uidx = np.sort(uidx)
        uidx[-1] = len(hsh) - 1  # Handle end of array
        nav_tx["lat"] = np.interp(idx, uidx, nav_tx["lat"][uidx])
        nav_tx["lon"] = np.interp(idx, uidx, nav_tx["lon"][uidx])
        nav_tx["hgt"] = np.interp(idx, uidx, nav_tx["hgt"][uidx])

        df = pd.DataFrame()
        # store average lat lon hgt
        df["lon"] = np.mean(np.vstack((nav_rx["lon"], nav_tx["lon"])), axis=0)
        df["lat"] = np.mean(np.vstack((nav_rx["lat"], nav_tx["lat"])), axis=0)
        df["hgt"] = np.mean(np.vstack((nav_rx["hgt"], nav_tx["hgt"])), axis=0)

        # project rx and tx lat lon hgt and get euclidean distance
        rx_df = pd.DataFrame()
        rx_df["x"], rx_df["y"], rx_df["z"] = xformer.transform(
            nav_rx["lon"].to_numpy(),
            nav_rx["lat"].to_numpy(),
            nav_rx["hgt"].to_numpy(),
        )
        tx_df = pd.DataFrame()
        tx_df["x"], tx_df["y"], tx_df["z"] = xformer.transform(
            nav_tx["lon"].to_numpy(),
            nav_tx["lat"].to_numpy(),
            nav_tx["hgt"].to_numpy(),
        )
        df["asep"] = np.sqrt((rx_df['x']-tx_df['x'])**2 + (rx_df['y']-tx_df['y'])**2 + (rx_df['z']-tx_df['z'])**2)

    elif "rxFix0" in k:
        df = pd.DataFrame(h5[grp]["rxFix0"][:])
    elif "ppp0" in k:
        df = pd.DataFrame(h5[grp]["ppp0"][:])
        df["asep"] = 50
    else:
        df = pd.DataFrame(h5[grp]["gps0"][:])
        df["asep"] = 50
    
    # if BSI ice radar, assume no antenna separation
    try:
        if "Blue Systems" in h5.attrs["system"]:
            df["asep"] = 0
    except:
        pass
    
    try:
        df.rename(columns={"hgt": "elev"}, inplace=True)
    except:
        pass

    h5.close()

    # interpolate
    df = interp_xords(df)

    # project coords
    df["x"], df["y"], df["z"] = xformer.transform(
        df["lon"].to_numpy(),
        df["lat"].to_numpy(),
        df["elev"].to_numpy(),
    )

    df["dist"] = euclid_dist(
        df["x"].to_numpy(),
        df["y"].to_numpy(),
        df["z"].to_numpy())

    df["twtt_wind"] = 0.0

    return df[["lon", "lat", "elev", "x", "y", "z", "twtt_wind", "asep", "dist"]]


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

    # transform to projected xords 
    xformer = get_xformer(navcrs, xyzsys[body])
    df["x"], df["y"], df["z"] = xformer.transform(
        df["lon"].to_numpy(),
        df["lat"].to_numpy(),
        df["elev"].to_numpy(),
    )

    df["dist"] = euclid_dist(
        df["x"].to_numpy(),
        df["y"].to_numpy(),
        df["z"].to_numpy())

    df["twtt_wind"] = 0.0

    return df[["lon", "lat", "elev", "x", "y", "z", "twtt_wind", "dist"]]


def getnav_uaf_kentech(navfile, navcrs, body):
    h5 = h5py.File(navfile, "r")

    if "loc0" in h5["raw"].keys():
        nav = h5["raw"]["loc0"][:]
        df = pd.DataFrame(nav)
        try:
            df.rename(columns={"hgt": "elev"}, inplace=True)
        except:
            pass        # Interpolate non-unique values
        hsh = nav["lat"] + nav["lon"] * 1e4
        idx = np.arange(0, len(hsh), 1)
        uniq, uidx = np.unique(hsh, return_index=True)
        uidx = np.sort(uidx)
        uidx[-1] = len(hsh) - 1  # Handle end of array
        df["lat"] = np.interp(idx, uidx, df["lat"][uidx])
        df["lon"] = np.interp(idx, uidx, df["lon"][uidx])
        df["elev"] = np.interp(idx, uidx, df["elev"][uidx])

    else:
        h5.close()
        print("No valid navigation data found in file %s" % navfile)
        sys.exit()

    h5.close()

    # transform to projected xords 
    xformer = get_xformer(navcrs, xyzsys[body])
    df["x"], df["y"], df["z"] = xformer.transform(
        df["lon"].to_numpy(),
        df["lat"].to_numpy(),
        df["elev"].to_numpy(),
    )

    df["dist"] = euclid_dist(
        df["x"].to_numpy(),
        df["y"].to_numpy(),
        df["z"].to_numpy())

    df["twtt_wind"] = 0.0

    return df[["lon", "lat", "elev", "x", "y", "z", "twtt_wind", "dist"]]


def getnav_cresis_mat(navfile, navcrs, body):
    f = h5py.File(navfile, "r")
    lon = f["Longitude"][:].flatten()
    lat = f["Latitude"][:].flatten()
    elev = f["Elevation"][:].flatten()
    f.close()

    df = pd.DataFrame({"lon": lon, "lat": lat, "elev": elev})

    # transform to projected xords 
    xformer = get_xformer(navcrs, xyzsys[body])
    df["x"], df["y"], df["z"] = xformer.transform(
        df["lon"].to_numpy(),
        df["lat"].to_numpy(),
        df["elev"].to_numpy(),
    )

    df["dist"] = euclid_dist(
        df["x"].to_numpy(),
        df["y"].to_numpy(),
        df["z"].to_numpy())

    df["twtt_wind"] = 0.0

    return df[["lon", "lat", "elev", "x", "y", "z", "twtt_wind", "dist"]]


def getnav_gssi(navfile, tnum, navcrs, body):
    if os.path.isfile(navfile):
        try:
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

            # transform to projected xords 
            xformer = get_xformer(navcrs, xyzsys[body])
            df["x"], df["y"], df["z"] = xformer.transform(
                df["lon"].to_numpy(),
                df["lat"].to_numpy(),
                df["elev"].to_numpy(),
            )

            df["dist"] = euclid_dist(
                df["x"].to_numpy(),
                df["y"].to_numpy(),
                df["z"].to_numpy())
    
        except Exception as err:

            nd = np.repeat(np.nan, tnum)
            df = pd.DataFrame({"lon": nd, "lat": nd, "elev": nd,
                                        "x": nd, "y": nd, "z": nd,
                                        "dist": nd})
    else:
        nd = np.repeat(np.nan, tnum)
        df = pd.DataFrame({"lon": nd, "lat": nd, "elev": nd,
                                    "x": nd, "y": nd, "z": nd,
                                    "dist": nd})

    df["twtt_wind"] = 0.0

    return df[["lon", "lat", "elev", "x", "y", "z", "twtt_wind", "dist"]]


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

            # transform to projected xords 
            xformer = get_xformer(navcrs, xyzsys[body])
            df["x"], df["y"], df["z"] = xformer.transform(
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

    df["twtt_wind"] = 0.0

    return df[["lon", "lat", "elev", "x", "y", "z", "twtt_wind", "dist"]]

    
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

    # SHARAD FPB sample 1800 corresponds to the areoid height - use areoid to reference elevation and get absolute twtt - aeroid height in meters after subtracting 3396000 m
    # aerPath = os.path.split(os.getcwd())[0] + "/dat/mars/mega90n000eb.tif"
    aerPath = os.path.join(os.path.dirname(__file__), '../dat/mars', 'mega90n000eb.tif')
    try:
        aer = rio.open(aerPath, mode="r")

    except:
        print("Unable to open areoid file. Is it located at : " + aerPath + " ?")
        sys.exit(1)

    try:
        # transform MRO lon/lat to areoid x/y to sample areoid radius along SC path 
        xformer = get_xformer(navcrs, aer.crs.to_proj4())
        aerX, aerY = xformer.transform(
            df["lon"].to_numpy(),
            df["lat"].to_numpy()
        )

        # get raster x/y index of SC x/y positions
        ix,iy = aer.index(aerX,aerY)

        ix = np.asarray(ix)
        iy = np.asarray(iy)

        # there seems to be a rasterio indexing error where value may exceed axis bounds when a track is pole-crossing
        # subtracting one from the index value seems to resolve this
        ix[ix > aer.width - 1] = aer.width - 1
        ix[ix < 0] = 0
        iy[iy > aer.height - 1] = aer.height - 1
        iy[iy < 0] = 0

        aerZ = aer.read(1)[ix,iy]

        # reference sc elevation to areoid height  = scRad - (3396km + aerZ)
        df["elev"] = (1000.0*df["scRad"]) - 3396000.0 - aerZ

        # elevation at top of radargram (sample 0) = aerZ + offset = aerZ + (1800 [samples] * 37.5e-9 [sec/sample] * 3e8 [m/sec] / 2)
        elevSamp0 = aerZ + (1800*37.5e-9*C/2)

        # get twtt window from sc to top of radargram = 2*(elev - evelSamp0)/c
        # this will be added back in upon export to get absolute twtt of picks
        df["twtt_wind"] = 2*((df["elev"]) - elevSamp0)/C

    except:
        print("SHARAD Areiod referencing error. Are the proper planetary body and coordinate reference system set in the config file?\nbody:\t{}\ncrs:\t{}".format(body,navcrs))
        sys.exit(1)

    return df[["lon", "lat", "elev", "x", "y", "z", "twtt_wind", "dist"]]


def getnav_lrs(navfile, navcrs, body, tnum):

    if navfile.endswith('.csv'):
        df = pd.read_csv(navfile, index_col=False)

        df["dist"] = euclid_dist(
            df["x"].to_numpy(),
            df["y"].to_numpy(),
            df["z"].to_numpy())

        df["elev"] = df["hgt"]

        df.rename(columns={"delay": "twtt_wind"}, inplace=True)

    elif navfile.endswith('.img'):
        # based on label file
        twtt_wind = []
        lon = []
        lat = []
        elev = []
        with open(navfile, "rb") as f:
            # loop through traces
            for _i in range(tnum):
                f.seek((_i*55)+23)
                twtt_wind.append(f.read(4))     # time delay is 4 bytes starting at 23
                f.read(2)
                lat.append(f.read(4))           # lat is 4 bytes starting at 29
                lon.append(f.read(4))           # lon is 4 bytes starting at 33
                elev.append(f.read(4))          # elev is 4 bytes starting at 37

        twtt_wind = np.frombuffer(np.asarray(twtt_wind), np.float32)
        lat = np.frombuffer(np.asarray(lat), np.float32)
        lon = np.frombuffer(np.asarray(lon), np.float32)
        elev = np.frombuffer(np.asarray(elev), np.float32)

        df = pd.DataFrame({'lon':lon,'lat':lat,'elev':elev,'twtt_wind':twtt_wind})

        # transform to projected xords 
        xformer = get_xformer(navcrs, xyzsys[body])
        df["x"], df["y"], df["z"] = xformer.transform(
            df["lon"].to_numpy(),
            df["lat"].to_numpy(),
            df["elev"].to_numpy(),
        )

        df["dist"] = euclid_dist(
            df["x"].to_numpy(),
            df["y"].to_numpy(),
            df["z"].to_numpy())
    
    # convert time delay from microseconds to seconds
    df["twtt_wind"] *= 1e-6
    
    return df[["lon", "lat", "elev", "x", "y", "z", "twtt_wind", "dist"]]


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

    # TODO: figure out what window before recording is for each trace
    df["twtt_wind"] = 0.0

    return df[["lon", "lat", "elev", "x", "y", "z", "twtt_wind", "dist"]]


def getnav_marsis_ipc(navfile, navcrs, body):

    geomCols = [
        "lat",
        "lon",
        "elev"
    ]
    df = pd.read_csv(navfile, names=geomCols, skiprows=1)

    # transform to projected xords 
    xformer = get_xformer(navcrs, xyzsys[body])
    df["x"], df["y"], df["z"] = xformer.transform(
        df["lon"].to_numpy(),
        df["lat"].to_numpy(),
        df["elev"].to_numpy(),
    )

    df["dist"] = euclid_dist(
        df["x"].to_numpy(),
        df["y"].to_numpy(),
        df["z"].to_numpy())


    df["twtt_wind"] = 0.0

    return df[["lon", "lat", "elev", "x", "y", "z", "twtt_wind", "dist"]]


def getnav_rimfax(navfile, navcrs, body):
    
    df = pd.read_csv(navfile, header=0)
    df = df.loc[df["record_type"]==0]
    idx = df.columns.get_loc("s0001")
    dat = np.array(df.iloc[:,idx:])
    # find traces with all null samples
    filt = ~np.isnan(dat).all(axis=1)                                                   
    df = df.iloc[filt,:idx]
    df.rename(columns={"ant_lat": "lat", "ant_lon": "lon", "ant_elev": "elev"}, inplace=True)

    # transform to projected xords 
    xformer = get_xformer(navcrs, xyzsys[body])
    df["x"], df["y"], df["z"] = xformer.transform(
        df["lon"].to_numpy(),
        df["lat"].to_numpy(),
        df["elev"].to_numpy(),
    )

    df["dist"] = euclid_dist(
        df["x"].to_numpy(),
        df["y"].to_numpy(),
        df["z"].to_numpy())


    df["twtt_wind"] = 0.0

    return df[["lon", "lat", "elev", "x", "y", "z", "twtt_wind", "dist"]]