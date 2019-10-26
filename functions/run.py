'''python function built to ingest HDF5 OIB-AK radar data
author: Brandon S. Tober
created: 24JUN19
'''
# import necessary libraries
import h5py
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl
import sys
if sys.version_info[0] < 3:
    import Tkinter as tk
else:
    import tkinter as tk

def ingest(in_path):

    # read in HDF5 .mat radar block file
    f = h5py.File(in_path, 'r')

    amp = np.array(f['block']['amp'])    
    ch0 = np.array(f['block']['ch0'])
    dist = np.array(f['block']['dist'])
    elev = np.array(f['block']['elev_air'])
    dt = f['block']['dt'][()]
    # print(list(f['block']))


    if 'chirp' in list(f['block'].keys()):    
        bw = f['block']['chirp']['bw'][()]   
        cf = f['block']['chirp']['cf'][()]    
        pLen = f['block']['chirp']['len'][()]

    return amp, dist, dt

def rgram(data, dist, dt, name):

    # show radargram in logarithmic scale with proper axes
    plt.imshow(np.log(np.power(data,2)), cmap='gray', aspect='auto', extent=[dist[0], dist[-1], data.shape[0] * dt * 1e6, 0])
    plt.title(name)
    plt.xlabel('along-track distance [km]')
    plt.ylabel('two-way travel time [microsec.]')
    plt.show()

    return


