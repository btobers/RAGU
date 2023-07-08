<img src="https://github.com/btobers/RAGU/raw/master/src/ragu/recs/ragu_logo.png" height="200">

# Radar Analysis Graphical Utility
### Authors: Brandon Tober and Michael Christoffersen
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.3968981.svg)](https://doi.org/10.5281/zenodo.3968981)

## What is RAGU?
RAGU is a user-interface radar interpretation software written in Python 3 and released under the GNU General Public License v3. RAGU was originally developed to ingest and interpret NASA Operation IceBridge airborne radar sounding data, but has been expanded for use with other sounder and ground penetrating radar datasets. While RAGU is primarily an interpretation software, minimal radar processing tools are included with the software.

### Dataset Capabilities:
RAGU was originally developed to work with NASA's Operation IceBridge Alaska radar sounding data. The dataset capabilities have since been expanded to include the following:

- NASA OIB-AK
- CReSIS (Radar Depth Sounder & Snow Radar)
- SHARAD (USRDR, USGEOM, US clutter sims)
- MARSIS (JPL multilook products)
- KAGUYA (SELENE) Lunar Radar Sounder (LRS)
- RIMFAX
- GSSI
- pulseEKKO

Have another radar dataset you'd like to be able to use RAGU to interpret? Please feel free to send the necessary python code to read in the data and we can incorporate an ingester. Or, feel free to collaborate and create an ingester for reading your data type with RAGU. Follow the ingester template: - *ingest/ingest_template.py*

### Package overview
- *config.py* script used to create the RAGU configuration file
- *bin/main.py* is run to start the RAGU app
- *ui/gui.py* handles the graphical user-interface and sets up the app
- *ui/impick.py* handles profile-view, radargram image picking
- *ui/wvpick.py* handles waveform-view picking optimization
- *ui/basemap.py* handles the basemap
- *ui/notepad.py* handles the notepad
- *radar/* contains radar data object information
- *radar/processing.py* performs simple user-specified radar data processing
- *ingest/* hadnles radar data ingest
- *nav/navparse.py* is used to parse radar gps data into the appropriate format and perform any necessary coordinate transformations
- *nav/gps.py*  is used to read and parse raw gps nmea strings into the appropriate format
- *tools/utils.py* contains a set of utility functions utilized by the app
- *tools/constants.py* contains global constants

### Outputs
#### Pick files:
1. **Comma-Separated Value (.csv)**
2. **Geopackage (.gpkg)**

    For **CSV** and **Geopackage** files, see the [format file](https://github.com/btobers/RAGU/raw/master/src/docs/RAGU_pk_format.pdf) in for per trace export attribute information.

#### Figure:
A figure each may also be exported for the uninterpreted radar profile, the accompanying clutter simulation, and the interpreted radar profile. Example over Malaspina Glacier, AK:  
<p align="center">
  <img src="https://github.com/btobers/RAGU/raw/master/src/ragu/recs/20190928-235534_compiled.jpg" height="500"><br>
</p>

#### Processing Script:
A file log/processing script may also be exported to keep track of and easily repeat any data processing steps. Example processing script:
```
### RAGU processing log ###
import sys
# change dir to RAGU code directory
sys.path.append('/home/user/code/RAGU/code')
from ingest import ingest

igst = ingest("/home/user/data/ARES/20140524-200130.h5")
rdata = igst.read("","+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs","earth")
rdata.lowpass(order=5, cf=1250000.0)
rdata.tpowGain(power=1.2)
```

## Running RAGU

### System Requirements
Supported Operating Systems:
- Linux (tested on Ubuntu 18.04, 20.04)
- Windows (tested on Windows 10)
- Mac (tested on Catalina)

### Dependencies
- tkinter
- matplotlib
- numpy
- scipy
- pandas
- geopandas
- pyproj
- rasterio
- h5py

### Setup
**Nonte: Prior to installation, one may first wish to create an anaconda environment from which to install ragu**.

1. Install ragu via [PyPi](https://pypi.org/project/ragu/)

```
$ pip install ragu
```

2. To run ragu, call ragu from the command line to initialize the GUI:
```
$ ragu
```
**Nonte: The first time ragu is run on your machine, a configuration file will be created at *~/RAGU/config.ini*.** This configuration file can be edited to set appropriate data paths, data coordinate reference system, and output preferences. Path variables may be left blank, but must remain uncommented. An example ragu configuration file can be found [here](https://github.com/btobers/RAGU/raw/master/src/docs/config.ini).


## Notes
Several auxiliary tools which RAGU users may find useful can be found at [radar_tools](https://github.com/btobers/radar_tools)

### Future Development
Additional dataset ingesters:
- Segy

Processing:
- gain
- filtering
- migration

Tools:
- depth conversion
- dielectric extraction
- pick amplitude tracking

General:
pyproj.transform is deprecated going from pyproj v1 to v2. Ragu.nav.navparse needs to be updated accordingly.

### Collaboration

Interested in contributing in the development of RAGU, or if you would like to use RAGU for interpreting a radar dataset that is not currently supported - Reach out to tobers.brandon@gmail.com


### Publications

A list of publications that cite RAGU:

1. Loso, Michael G., Christopher F. Larsen, Brandon S. Tober, Michael Christoffersen, Mark Fahnestock, John W. Holt, and Martin Truffer. “Quo Vadis, Alsek? Climate-Driven Glacier Retreat May Change the Course of a Major River Outlet in Southern Alaska.” Geomorphology 384 (July 1, 2021): 107701. https://doi.org/10.1016/j.geomorph.2021.107701.
2. Tober, B. S., J. W. Holt, M. S. Christoffersen, M. Truffer, C. F. Larsen, D. J. Brinkerhoff, and S. A. Mooneyham. “Comprehensive Radar Mapping of Malaspina Glacier (Sít’ Tlein), Alaska—The World’s Largest Piedmont Glacier—Reveals Potential for Instability.” Journal of Geophysical Research: Earth Surface 128, no. 3 (2023): e2022JF006898. https://doi.org/10.1029/2022JF006898.