# NOSEpick
## Nearly Optimal Subsurface Extractor GUI
### Authors: Brandon Tober and Michael Christoffersen
[![DOI](https://zenodo.org/badge/193940796.svg)](https://zenodo.org/badge/latestdoi/193940796)

<p align="center">
  <img src="recs/NOSEpick.png" height="200"><br>
  NOSEpick logo artist: Eric Petersen<br><br>
  <img src="recs/NOSEpick_demo.gif" height="500">
</p>

## Description
NOSEpick is an open source GUI package developed to interpret radar sounding data, written in Python 3.

### File Info
- *nose_env.yml* contains a list of NOSEpick dependencies
- *config.ini* contains user-specified configuration file paths and information necessary to run the NOSEpick app
- *main.py* is run to start the NOSEpick app
- *ui/gui.py* handles the graphical user-interface and sets up the app
- *ui/impick.py* handles profile-view, radargram image picking
- *ui/wvpick.py* handles waveform-view picking optimization
- *ui/basemap.py* handles the basemap
- *radar/* contains radar data object information
- *radar/processing.py* performs simple user-specified radar data processing
- *ingest/* hadnles radar data ingest
- *nav/navparse.py* is used to parse radar gps data into the appropriate format and perform any necessary coordinate transformations
- *nav/gps.py*  is used to read and parse raw gps nmea strings into the appropriate format
- *tools/utils.py* contains a set of utility functions utilized by the app
- *tools/constants.py* contains uglobal constants

### Dataset Capabilities:
NOSEpick was originally developed to work with NASA's Operation IceBridge Alaska radar sounding data. NOSEpick is also capable of working with SHARAD data acquired onboard NASA's Mars Reconnaissance Orbiter (Reduced Data Record of Radar Backscatter Power (USRDR) & Geographic, Geometric, and Ionospheric Properties (USGEOM) data available at https://pds-geosciences.wustl.edu/missions/mro/sharad.htm). GSSI data can also be interpreted with NOSEpick.

- NASA OIB-AK
- SHARAD (USRDR, USGEOM, US clutter sims)
- GSSI

## System Requirements
Supported Operating Systems:
- Linux (tested on Ubuntu 18.04, 20.04)
- Windows (tested on Windows 10)
- Mac (tested on Catalina)

## Dependencies
- tkinter
- matplotlib
- numpy
- scipy
- pandas
- geopandas
- pyproj
- rasterio
- h5py

To create a conda environment with the required dependencies, run the following command:
```
$ conda env create -f nose_env.yml
```

## Running NOSEpick
1. Prior to running NOSEpick, set appropriate data paths, data coordinate reference system, and output preferences in *config.ini*:
```
### config.ini ###
[path]
# str datPath: data directory path
datPath = /home/btober/Documents/SHARAD_test/
# str simPath: clutter simulation directory path
simPath = /home/btober/Documents/SHARAD_test/simc/
# str mapPath: basemap directory path
mapPath = /home/btober/Documents/SHARAD_test/MOLA/
# str outPath: output directory path
outPath = /home/btober/Documents/SHARAD_test/

[nav]
# str body: planetary body from which radar data was acquired
body = mars
# str navcrs: crs string
crs = +proj=longlat +a=3396190 +b=3376200 +no_defs

[output]
# float eps_r: relative permittivity (dielectric constant), required for plotting in depth and calculating layer thickness
eps_r = 3.15
# bool amp: export pick amplitudes
amp = True
# bool csv: export csv file of picks
csv = True
# bool shp: export shapefile of picks
shp = True
# bool fig: export profile image with picks
fig = True
```

2a. Activate NOSEpick anaconda environment - 'nose' by default:
```
$ conda activate nose
(nose)$ python main.py
```

2b. If the default Python environment is not set as Python 3, specify:
```
$ python3 main.py
```

## Notes
NOSEpick is still in development, but is in operable standing for interpreting certain datasets. 
Plans for the future are to complete the wvPick optimization tools, as well as add ingesters for additional datasets. So far, the thought is to add a ingester for PulsEKKO, Mala, and segy data. A SHARAD ingester as well as a GSSI ingester (thanks to https://github.com/iannesbitt/readgssi) have been added and are still in development stages. GSSI data is currently ingested without gps data. A segy ingester is also in the works.
Furutre development plans also invlude finding a way to render images faster when toggling between radar data and clutter, zooming/resetting the view. This can possible be done by down-sampling the data based on the zoom.

### Desktop Shortcut
If desired, pyshorcuts can be used to create a desktop shortcut:

If not already installed, install pyshortcuts:
```
$ pip install pyshortcuts
```

Use pyshortcuts to setup desktop shortcut (make sure NOSEpick conda environment is activated - 'nose' by default):
```
$ conda activate nose
(nose)$ pyshortcut -n NOSEpick -i ~/NOSEpick/recs/NOSEpick.ico ~/NOSEpick/code/main.py
```
