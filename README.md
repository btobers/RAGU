# NOSEpick
## Nearly Optimal Subsurface Extractor GUI
### Authors: Brandon Tober and Michael Christoffersen

<p align="center">
  <img src="lib/NOSEpick.png" height="200"><br>
  NOSEpick logo artist: Eric Petersen<br><br>
  <img src="lib/NOSEpick_demo.gif" height="500">
</p>

## Description
NOSEpick is an open source GUI package developed to interpret radar sounding data, written in Python 3. This was originally developed to work with NASA's Operation IceBridge Alaska radar sounding data. NOSEpick is also capable of work with SHARAD data acquired onboard NASA's Mars Reconnaissance Orbiter (Reduced Data Record of Radar Backscatter Power (USRDR) & Geographic, Geometric, and Ionospheric Properties (USGEOM) data available at https://pds-geosciences.wustl.edu/missions/mro/sharad.htm). GSSI data can also be interpreted with NOSEpick.

- *main.py* is run to begin the NOSEpick app
- *config.py* contains user-specified configuration file paths necessary to run the NOSEpick app
- *constants.py* contains uglobal constants
- *gui.py* initializes the graphical user-interface tools and sets up the app
- *ingester.py* is used to ingest radar data
- *readgssi.py* is used to parse gssi data (pulled from https://github.com/iannesbitt/readgssi)
- *imPick.py* handles the image picking portion of the app
- *wvPick.py* handles the wave picking optimization portion of the app
- *basemap.py* handles the basemap portion of the app
- *nav.py* handles navigation data and nav coordinate transformations
- *utils.py* contains a set of utility functions utilized by the app
- *nose_env.yml* contains list of the dependencies

To create a conda environment with the required dependencies, run the following command:
```
$ conda env create -f nose_env.yml
```
    
## Running NOSEpick
Prior to running NOSEpick, set appropriate data paths in *config.py*

To run NOSEpick, first activate NOSEpick anaconda environment - 'nose' by default:
```
$ conda activate nose
(nose)$ python main.py
```

If the default Python environment is not set as Python 3, you will have to specify:
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
(nose)$ pyshortcut -n NOSEpick -i ~/NOSEpick/lib/NOSEpick.ico ~/NOSEpick/main.py
```
