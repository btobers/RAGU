# NOSEpick
Nearly Optimal Subsurface Extractor GUI

Authors: Brandon Tober and Michael Christoffersen

## Description
NOSEpick is an open source GUI package developed to interpret radar sounding data, written in Python 3. This was originally developed to work with NASA's Operation IceBridge Alaska radar sounding data. 
- *main.py* is run to begin the NOSEpick app
- *gui.py* initializes the graphical user-interface tools and sets up the app
- *ingester.py* is used to ingest radar data
- *imPick.py* handles the image picking portion of the app
- *wvPick.py* handles the wave picking optimization portion of the app
- *basemap.py* handles the basemap portion of the app
- *nav.py* handles navigation data and nav coordinate transformations
- *utils.py* contains a set of utility functions utilized by the app
- *nose_env.yml* contains the dependencies to run the app

To create a conda environment with the required dependencies, run the following command:
.. code-block:: bash

    $ conda env create -f nose_env.yml
    
## Running NOSEpick
Prior to running NOSEpick, set appropriate data paths in *main.py*

To run NOSEpick:
.. code-block:: bash

    (nose)$ python main.py
