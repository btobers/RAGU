# RAGU - Radar Analysis Graphical Utility
#
# copyright © 2020 btobers <tobers.brandon@gmail.com>
#
# distributed under terms of the GNU GPL3.0 license
"""
RAGU radar data processing class and tools
"""
### imports ###
from tools import utils
import numpy as np
import numpy.matlib as matlib
import matplotlib.pyplot as plt
import scipy.interpolate as interp
import scipy.signal as signal

class proc(object):
    def __init__(self):
        #: np.ndarray(snum x tnum), previously processed radar data (amp)
        self.prev_amp = None
        #: np.ndarray(snum x tnum), previously processed radar data (dB)
        self.prev_dB = None
        #: np.ndarray(snum x tnum), current processed radar data (amp)
        self.curr_amp = None
        #: np.ndarray(snum x tnum), current processed radar data (dB)
        self.curr_dB = None

    def set_prev_amp(self, amp):
        self.prev_amp = amp

    def get_prev_amp(self):
        return self.prev_amp

    def set_prev_dB(self, dB):
        self.prev_dB = dB

    def get_prev_dB(self):
        return self.prev_dB

    def set_curr_amp(self, amp):
        self.curr_amp = amp

    def get_curr_amp(self):
        return self.curr_amp

    def set_curr_dB(self, dB):
        self.curr_dB = dB

    def get_curr_dB(self):
        return self.curr_dB


def set_tzero(self):
    # get mean trace and find max sample and update sampzero flag
    meanTrace = np.mean(np.abs(self.dat), axis=1)
    self.flags.sampzero = np.nanargmax(meanTrace)

    if self.flags.sampzero > 0:
        self.tzero_shift()
        # log
        out = '# Time zero shifted to:\n# sample:\t {}\n# time:\t\t {} nanoseconds'\
        .format(self.flags.sampzero,(self.flags.sampzero * self.dt * 1e9))
        self.log("self.rdata.set_tzero()" + "\n" + out)
        print(out)

    return


def tzero_shift(self):
    # shift 2d proc data array so first row is time zero sample - use nan to fill bottom samples
    amp = self.proc.get_curr_amp()
    self.proc.set_prev_amp(amp)
    self.proc.set_prev_dB(self.proc.get_curr_dB())
    out = np.zeros_like(amp)
    out[:-self.flags.sampzero,:] = amp[self.flags.sampzero:,:]
    out[-self.flags.sampzero:,:] = np.nan
    self.set_proc(out)

    return


def butter(btype="lowpass", lowcut=None, highcut=None, fs=None, order=5):
    nyq = 0.5 * fs
    cutoff = []
    if btype=="lowpass" and highcut > 0:
        cutoff.append(highcut / nyq)
    elif btype=="highpass" and lowcut > 0:
        cutoff.append(lowcut / nyq)
    elif btype=="bandpass" and lowcut > 0 and highcut > 0:
        cutoff.append(lowcut / nyq)
        cutoff.append(highcut / nyq)
    else:
        raise ValueError("Critical frequency error: Lowcut={}, Highcut={}".format(lowcut, highcut))
        return
    b, a = signal.butter(order, cutoff, btype=btype)

    return b, a


def hilbertxform(self):
    amp = self.proc.get_curr_amp()
    self.proc.set_prev_amp(amp)
    self.proc.set_prev_dB(self.proc.get_curr_dB())
    analytic_signal = signal.hilbert(amp, axis=0)
    amplitude_envelope = np.abs(analytic_signal)
    self.set_proc(amplitude_envelope)
    # log
    self.log("self.rdata.hilbertxform()")
    print("# hilbert transform applied applied")

    return 


def filter(self, btype="lowpass", lowcut=None, highcut=None, order=5, direction=0):
    # apply low pass filter to data array
    amp = self.proc.get_curr_amp()
    self.proc.set_prev_amp(amp)
    self.proc.set_prev_dB(self.proc.get_curr_dB())
    if direction == 0:
        fs=1/self.dt
    elif direction == 1:
        fs=self.prf
    b, a = butter(btype=btype, lowcut=lowcut, highcut=highcut, fs=fs, order=order)
    out = signal.filtfilt(b, a, np.abs(amp), axis=direction)
    # use amplitude of lp filtered data to reset as pc array
    self.set_proc(out)
    # log
    self.log("self.rdata.filter(btype='{}', lowcut={}, highcut={}, order={}, direction={})".format(btype, lowcut, highcut, order, direction))
    print("# filter applied: btype='{}', lowcut={}, highcut={}, order={}, direction={})".format(btype, lowcut, highcut, order, direction))

    return


def tpowGain(self, power):
    # t-power gain to each trace with the given exponent.
    amp = self.proc.get_curr_amp()
    self.proc.set_prev_amp(amp)
    self.proc.set_prev_dB(self.proc.get_curr_dB())
    twtt = np.arange(self.snum)*self.dt
    factor = np.reshape(twtt**(float(power)),(len(twtt),1))
    factmat = np.matlib.repmat(factor,1,self.tnum)
    out = np.multiply(amp,factmat)
    self.set_proc(out)
    # log
    self.log("self.rdata.tpowGain(power={})".format(power))
    print("# time^{} gain applied".format(power))

    return


def undo(self):
    # undo last processing step
    if len(self.hist) > 2:
        tmp = self.proc.get_curr_amp()
        self.set_proc(self.proc.get_prev_amp())
        self.proc.set_prev_amp(tmp)
        # clear last log entry
        self.last = self.hist[-1]
        del self.hist[-1]

    return


def redo(self):
    tmp = self.proc.get_curr_amp()
    self.set_proc(self.proc.get_prev_amp())
    self.proc.set_prev_amp(tmp)
    self.log(self.last)

    return


def reset(self):
    # reset processed data to original
    if self.dtype == "oibak":
        self.set_proc(np.abs(self.dat))

    else:
        self.set_proc(self.dat)

    # clear log of all processing
    del self.hist[2:]
    
    return


### proc functions still in dev ###

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