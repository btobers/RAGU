# RAGU - Radar Analysis Graphical Utility
#
# copyright © 2020 btobers <tobers.brandon@gmail.com>
#
# distributed under terms of the GNU GPL3.0 license
"""
RAGU radar data processing tools
"""
### imports ###
import numpy as np
import numpy.matlib as matlib
import scipy.interpolate as interp
import scipy.signal as signal
import matplotlib.pyplot as plt
import matplotlib as mpl
import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.widgets import Button


def get_tzero(raw):
    """
    get time zero of radar data based on average trace
    INPUT:
    raw         raw data matrix whose columns contain the traces 

    OUTPUT:
    samp        sample number to set as time zero
    """
    # get mean trace and find max sample
    meanTrace = np.mean(np.abs(raw), axis=1)
    samp = np.nanargmax(meanTrace)
    return samp

def tzero_shift(samp, raw):
    """
    get time zero of radar data based on average trace
    INPUT:
    samp        sample number to shift to time zero
    raw         raw data matrix whose columns contain the traces 

    OUTPUT:
    out         shifted output data array
    """
    if samp > 0:    
        # roll data and set last chunk as nan
        out = np.zeros(raw.shape)
        out[:-samp,:] = raw[samp:,:]
        out[-samp:,:] = np.nan

    else:
        out = raw
    return out

def dewow(data,window):
    """
    Subtracts from each sample along each trace an 
    along-time moving average.

    Can be used as a low-cut filter.

    INPUT:
    data       data matrix whose columns contain the traces 
    window     length of moving average window 
               [in "number of samples"]

    OUTPUT:
    newdata    data matrix after dewow
    """
    totsamps = data.shape[0]
    # If the window is larger or equal to the number of samples,
    # then we can do a much faster dewow
    if (window >= totsamps):
        newdata = data-np.matrix.mean(data,0)            
    else:
        newdata = np.asmatrix(np.zeros(data.shape))
        halfwid = int(np.ceil(window/2.0))
        
        # For the first few samples, it will always be the same
        avgsmp=np.matrix.mean(data[0:halfwid+1,:],0)
        newdata[0:halfwid+1,:] = data[0:halfwid+1,:]-avgsmp

        # for each sample in the middle
        for smp in range(halfwid,totsamps-halfwid+1):
            winstart = int(smp - halfwid)
            winend = int(smp + halfwid)
            avgsmp = np.matrix.mean(data[winstart:winend+1,:],0)
            newdata[smp,:] = data[smp,:]-avgsmp

        # For the last few samples, it will always be the same
        avgsmp = np.matrix.mean(data[totsamps-halfwid:totsamps+1,:],0)
        newdata[totsamps-halfwid:totsamps+1,:] = data[totsamps-halfwid:totsamps+1,:]-avgsmp
        
    return newdata


def remMeanTrace(data,ntraces):
    """
    Subtracts from each trace the average trace over
    a moving average window.

    Can be used to remove horizontal arrivals, 
    such as the airwave.

    INPUT:
    data       data matrix whose columns contain the traces 
    ntraces    window width; over how many traces 
               to take the moving average.

    OUTPUT:
    newdata    data matrix after subtracting average traces
    """

    data=np.asmatrix(data)
    tottraces = data.shape[1]
    # For ridiculous ntraces values, just remove the entire average
    if ntraces >= tottraces:
        newdata=data-np.matrix.mean(data,1) 
    else: 
        newdata = np.asmatrix(np.zeros(data.shape))    
        halfwid = int(np.ceil(ntraces/2.0))
        
        # First few traces, that all have the same average
        avgtr=np.matrix.mean(data[:,0:halfwid+1],1)
        newdata[:,0:halfwid+1] = data[:,0:halfwid+1]-avgtr
        
        # For each trace in the middle

        for tr in range(halfwid,tottraces-halfwid+1):   
            winstart = int(tr - halfwid)
            winend = int(tr + halfwid)
            avgtr=np.matrix.mean(data[:,winstart:winend+1],1)                
            newdata[:,tr] = data[:,tr] - avgtr

        # Last few traces again have the same average    
        avgtr=np.matrix.mean(data[:,tottraces-halfwid:tottraces+1],1)
        newdata[:,tottraces-halfwid:tottraces+1] = data[:,tottraces-halfwid:tottraces+1]-avgtr
    print("rolling mean trace removed: window size: \t" + str(ntraces) + " traces")
    return newdata


def lowpassFilt(pc, order = 5, Wn = 1e6, fs = None):
    [b, a] = signal.butter(order, Wn, btype="lowpass", fs=fs)
    pc_lp = signal.filtfilt(b, a, pc, axis=0)
    print("lowpass filter applied")
    return np.abs(pc_lp) 


def agcGain(data, window=50, scaling_factor=50):
    """Try to do some automatic gain control

    Parameters
    ----------
    window: int, optional
        The size of window we use in number of samples (default 50)
    scaling_factor: int, optional
        The scaling factor. This gets divided by the max amplitude when we rescale the input.
        Default 50.
    """
    num_sample = data.shape[1]
    maxamp = np.zeros((num_sample,))
    for i in range(num_sample):
        maxamp[i] = np.max(np.abs(data[max(0, i - window // 2):
                                            min(i + window // 2, num_sample), :]))
    maxamp[maxamp == 0] = 1.0e-6
    newdata = data * (scaling_factor / np.atleast_2d(maxamp).transpose()).astype(data.dtype)

    return newdata


def tpowGain(data, twtt, power):
    """
    Apply a t-power gain to each trace with the given exponent.

    INPUT:
    data      data matrix whose columns contain the traces
    twtt      two-way travel time values for the rows in data
    power     exponent

    OUTPUT:
    newdata   data matrix after t-power gain
    """
    factor = np.reshape(twtt**(float(power)),(len(twtt),1))
    factmat = np.matlib.repmat(factor,1,data.shape[1])
    out = np.multiply(data,factmat)
    print("t^" + str(power) + " gain applied")
    return out


def shiftSim(data, shift):
    """
    apply lateral shift to clutter sim to line up with data.
    INPUT:
    data      data matrix whose columns contain the traces
    shift     lateral shift [# columns]
    prf       pulse repitition frequency to get total time of shift
    
    OUTPUT:
    out_sim rolled sim array
    """
    out = np.roll(data, shift, axis=1)
    return out


def restore(dtype, dat):
    if dtype == "oibak":
        return np.abs(dat)
    elif dtype == "gssi":
        return dat
    elif dtype == "sharad":
        return dat
    else:
        print("processing error: restore received unknown data type, " + dtype)