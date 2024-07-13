# RAGU - Radar Analysis Graphical Utility
#
# copyright © 2020 btobers <tobers.brandon@gmail.com>
#
# distributed under terms of the GNU GPL3.0 license
"""
RAGU radar data processing class and tools
"""
### imports ###
from ragu.tools import utils
from ragu.nav import navparse
import pyproj
import numpy as np
import pandas as pd
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
    if self.info["Signal Type"] == "Chirp":
        meanTrace = np.nanmean(np.abs(self.dat), axis=1)
        self.flags.sampzero = np.nanargmax(meanTrace)
    elif self.info["Signal Type"] == "Impulse":
        self.flags.sampzero = np.nanmean(utils.get_srf(np.abs(self.dat), "Impulse")).astype(int)

    if self.flags.sampzero > 0:
        self.tzero_shift()
        # log
        out = '# Time zero shifted to:\n# sample:\t {}\n# time:\t\t {} nanoseconds'\
        .format(self.flags.sampzero,(self.flags.sampzero * self.dt * 1e9))
        self.log("rdata.set_tzero()" + "\n" + out)
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


def reverse(self):
    # reverse left-right order of radargram
    self.set_dat(self.get_dat()[:,::-1])
    self.set_proc(self.get_dat())

    # need to flip all relevant arrays - nav, picks, clutter
    if self.flags.sim:
        self.set_sim(utils.powdB2amp(self.sim)[:,::-1])

    # flip navdf and recalculate distance array
    self.navdf = self.navdf.iloc[::-1].reset_index(drop=True)
    self.navdf.dist = navparse.euclid_dist(self.navdf.x.to_numpy(), self.navdf.y.to_numpy(), self.navdf.z.to_numpy())

    # reverse picks
    for h in self.pick.horizons.keys():
        self.pick.horizons[h] = np.flip(self.pick.horizons[h])

    # log
    self.log("rdata.rgram_reverse()")
    print("# radargram reversed, to undo simply repeat reverse operation")

    return

def flatten(self):
    # flatten radargram by rolling each trace so that the surface is at sample zero
    amp = self.proc.get_curr_amp()
    self.proc.set_prev_amp(amp)
    self.proc.set_prev_dB(self.proc.get_curr_dB())
    # initialize output array
    out = np.zeros_like(amp.T)
    # get surf samples in integer form for rolling
    self.flags.sampzero = self.pick.horizons[self.pick.get_srf()].astype(int)
    # loop through all traces and roll according to surface sample
    for i, col in enumerate(amp.T):
        out[i] = np.roll(col, shift = -self.flags.sampzero[i])
        out[i][-self.flags.sampzero[i]:] = np.nan             # set prior air samples to nan?

    self.set_proc(out.T)

    # log
    self.log("rdata.flatten()")
    print("# data array flattened ")

    return


def vertical_roll(self, samples=0):
    # roll 2d proc data array vertically to fix mismatch
    amp = self.proc.get_curr_amp()
    self.proc.set_prev_amp(amp)
    self.proc.set_prev_dB(self.proc.get_curr_dB())
    out = np.roll(amp, shift=samples, axis=0)
    self.set_proc(out)

    # log
    self.log("rdata.vertical_roll(samples={})".format(samples))
    print("# data array rolled by {} samples".format(samples))

    return


def removeSlidingMeanFFT(self, window):
    # background noise removal using sliding mean in frequency space
    amp = self.proc.get_curr_amp()
    self.proc.set_prev_amp(amp)
    self.proc.set_prev_dB(self.proc.get_curr_dB())

    # window in interval to avg over for mean removal
    mean = np.zeros(amp.shape)
    a = np.zeros(amp.shape[1])
    a[0 : window // 2] = 1
    a[amp.shape[1] - window // 2 : amp.shape[1]] = 1
    A = np.fft.fft(a)

    # Main circular convolution
    for i in range(amp.shape[0]):
        T = np.fft.fft(amp[i, :])
        mean[i, :] = np.real(np.fft.ifft(np.multiply(T, A)) / window)

    # Handle edges
    mt = np.zeros(amp.shape[0])
    for i in range(0, window):
        mt = np.add(mt, np.divide(amp[:, i], window))

    for i in range(0, window // 2):
        mean[:, i] = mt

    mt = np.zeros(amp.shape[0])
    for i in range(amp.shape[1] - window, amp.shape[1]):
        mt = np.add(mt, np.divide(amp[:, i], window))

    for i in range(amp.shape[1] - window // 2, amp.shape[1]):
        mean[:, i] = mt

    out = np.subtract(amp, mean)
    self.set_proc(out)
    # log
    self.log("rdata.removeSlidingMeanFFT(window={})".format(window))
    print("# Background removal completed wtih a window size of {} traces".format(window))

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
    self.log("rdata.hilbertxform()")
    print("# hilbert transform applied applied")

    return 


def filter(self, btype="lowpass", lowcut=None, highcut=None, order=5, direction=0):
    # apply low pass filter to data array
    amp = self.proc.get_curr_amp()
    self.proc.set_prev_amp(amp)
    # use abs value of amp
    amp = np.abs(amp)
    self.proc.set_prev_dB(self.proc.get_curr_dB())
    if direction == 0:
        fs=1/self.dt
    elif direction == 1:
        fs=self.prf
    b, a = butter(btype=btype, lowcut=lowcut, highcut=highcut, fs=fs, order=order)
    # avoid scipy filter nan issues by windowing out any time zero shift
    out = np.zeros_like(amp)
    # get indices of any nans and temporarily replace
    idx = np.where(np.isnan(amp))
    amp[idx] = -9999
    out = signal.filtfilt(b, a, amp, axis=direction)
    out[idx] = np.nan
    # out[:-self.flags.sampzero,:] = signal.filtfilt(b, a, np.abs(amp[:-self.flags.sampzero:,:]), axis=direction)
    # out[-self.flags.sampzero:,:] = np.nan
    # use amplitude of lp filtered data to reset as pc array
    self.set_proc(out)
    # log
    self.log("rdata.filter(btype='{}', lowcut={}, highcut={}, order={}, direction={})".format(btype, lowcut, highcut, order, direction))
    print("# filter applied: btype='{}', lowcut={}, highcut={}, order={}, direction={}".format(btype, lowcut, highcut, order, direction))

    return


def restack(self, intrvl=None,thold=None):
    # get coordinate transformation
    xform = pyproj.Transformer.from_crs(self.geocrs, self.xyzcrs)

    # restack radar data to specified along-track distance
    amp = self.proc.get_curr_amp()
    self.proc.set_prev_amp(amp)
    navdf = self.navdf.copy()
    # first account for any static traces where there may be gps drift
    if thold > 0:
        consecutive_dist = np.zeros_like(navdf.x)
        consecutive_dist[1:] = np.sqrt(np.diff(navdf.x.to_numpy()) ** 2.0 + np.diff(navdf.y.to_numpy()) ** 2.0 + np.diff(navdf.z.to_numpy()) ** 2.0)
        drift_mask = consecutive_dist >= thold

        # drop data from these traces
        namp = amp[:,drift_mask]
        navdf = navdf[drift_mask]
        navdf = navdf.reset_index(drop=True)
        # recalculcate distance after accounting for gps drift
        navdf["dist"] = navparse.euclid_dist(navdf["x"], navdf["y"], navdf["z"])
        self.snum, self.tnum = namp.shape
        amp = namp
        # get surface elev
        navdf['srfelev'] = self.srfElev[drift_mask]

    totdist = navdf.dist.iloc[-1]  # Total distance
    ntrace = int(totdist//intrvl)

    rstack = np.zeros((self.snum, ntrace))
    lat = np.zeros(ntrace)
    lon = np.zeros(ntrace)
    hgt = np.zeros(ntrace)
    srf = np.repeat(np.nan,ntrace)
    asep = np.repeat(np.nan,ntrace)
    twtt_wind = np.repeat(np.nan,ntrace)

    if "asep" not in navdf.keys():
        navdf["asep"] = self.asep
        
    for i in range(ntrace):
        stack_slice = np.logical_and(navdf.dist > i*intrvl, navdf.dist < (i+1)*intrvl)
        nstack = np.sum(stack_slice)
        if(nstack == 0):
            if i==0:
                rstack[:, i] = amp[:, i]
                lat[i] = navdf["lat"][i]
                lon[i] = navdf["lon"][i]
                hgt[i] = navdf["elev"][i]
                srf[i] = navdf["srfelev"][i]
                twtt_wind[i] = navdf["twtt_wind"][i]
                asep[i] = navdf["asep"][i]
            else:
                rstack[:, i] = rstack[:, i-1]
                lat[i] = lat[i-1]
                lon[i] = lon[i-1]
                hgt[i] = hgt[i-1]
                srf[i] = srf[i-1]
                twtt_wind[i] = twtt_wind[i-1]
                asep[i] = asep[i-1]
            continue

        rstack[:, i] = np.sum(amp[:, stack_slice], axis=1)/nstack
        lat[i] = np.mean(navdf["lat"][stack_slice])
        lon[i] = np.mean(navdf["lon"][stack_slice])
        hgt[i] = np.mean(navdf["elev"][stack_slice])
        srf[i] = np.mean(navdf["srfelev"][stack_slice])
        twtt_wind[i] = np.mean(navdf["twtt_wind"][stack_slice])
        asep[i] = np.mean(navdf["asep"][stack_slice])

    # store updated nav data
    self.navdf = pd.DataFrame()
    self.navdf["lon"] = lon
    self.navdf["lat"] = lat
    self.navdf["elev"] = hgt
    self.navdf["twtt_wind"] = twtt_wind
    self.navdf["asep"] = asep
    self.asep = asep

    self.set_srfElev(dat = srf)

    self.navdf["x"], self.navdf["y"], self.navdf["z"] = xform.transform(self.navdf["lon"], self.navdf["lat"], self.navdf["elev"])
    self.navdf["dist"] = navparse.euclid_dist(self.navdf["x"], self.navdf["y"], self.navdf["z"])

    self.snum, self.tnum = rstack.shape
    self.set_proc(rstack)
    # log
    self.log("rdata.restack(intrvl={},thold={})".format(intrvl,thold))
    print("# data restacked at an interval of {} m, with a minimum distance threshold of {} m".format(intrvl,thold))
    
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
    self.log("rdata.tpowGain(power={})".format(power))
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
        print("# last processing step removed")

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