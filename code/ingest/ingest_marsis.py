"""
ingest_marsis is a module developed to ingest JPL MARSIS radar sounding data. 
data format is binary 32-bit floating point pulse compressed power-dB data acquired from CO-SHARPS
"""
### imports ###
from radar import radar
from nav import navparse
from tools import utils
import imageio
import numpy as np
import os, sys, glob
import matplotlib.pyplot as plt

# method to read JPL multilook MARSIS data
def read(fpath, simpath, navcrs, body):
    orbit = "orbit_6549"
    fn = fpath.split("/")[-1]
    root = fpath.rstrip(fn)
    print("----------------------------------------")
    print("Loading: " + orbit + "/" + fn)
    rdata = radar(fpath)
    rdata.fn = orbit.split("_")[1] + fn.rstrip(".dat")
    rdata.dtype = "marsis"

    # convert binary RGRAM to numpy array
    # # reshape array
    dtype = np.dtype("float32")     
    with open(fpath, "rb") as f:
        dat = np.fromfile(f, dtype)     
    l = len(dat)

    rdata.snum = 2048
    # get number of traces, dividing file length by number of samples per trace, by 8 data arrays
    rdata.tnum = int(l/rdata.snum/8)
    # dt per pixel from reprocessed oversampled data
    rdata.dt = 1/(2*(1.4e6))
    rdata.nchan = 2

    # reshape into 8 stacked rgrams
    dat = dat.reshape((rdata.snum*8,rdata.tnum),order="F")

    # fig,axs = plt.subplots(4,2,figsize=(8, 6))
    # axs[0,0].imshow(10*np.log10(dat[0*2048:(1)*2048]),cmap="Greys_r")
    # axs[0,0].set_title("1")
    # axs[0,0].set_aspect('auto')

    # axs[0,1].imshow(10*np.log10(dat[1*2048:(2)*2048]),cmap="Greys_r")
    # axs[0,1].set_title("2")
    # axs[0,1].set_aspect('auto')

    # axs[1,0].imshow(10*np.log10(dat[2*2048:(3)*2048]),cmap="Greys_r")
    # axs[1,0].set_title("3")
    # axs[1,0].set_aspect('auto')

    # axs[1,1].imshow(10*np.log10(dat[3*2048:(4)*2048]),cmap="Greys_r")
    # axs[1,1].set_title("4")
    # axs[1,1].set_aspect('auto')

    # axs[2,0].imshow(10*np.log10(dat[4*2048:(5)*2048]),cmap="Greys_r")
    # axs[2,0].set_title("5")
    # axs[2,0].set_aspect('auto')

    # axs[2,1].imshow(10*np.log10(dat[5*2048:(6)*2048]),cmap="Greys_r")
    # axs[2,1].set_title("6")
    # axs[2,1].set_aspect('auto')

    # axs[3,0].imshow(10*np.log10(dat[6*2048:(7)*2048]),cmap="Greys_r")
    # axs[3,0].set_title("7")
    # axs[3,0].set_aspect('auto')

    # axs[3,1].imshow(10*np.log10(dat[7*2048:]),cmap="Greys_r")
    # axs[3,1].set_title("8")
    # axs[3,1].set_aspect('auto')

    # fig.tight_layout()
    # # # plt.subplots_adjust(wspace=0)
    # # mng = plt.get_current_fig_manager()
    # # mng.resize(*mng.window.maxsize())
    # # for _i in range(8):
    # #     print(np.mean(dat[_i*2048:(_i+1)*2048]), np.std(dat[_i*2048:(_i+1)*2048]))
    # #     axs[_i].imshow(10*np.log10(dat[_i*2048:(_i+1)*2048]),cmap="Greys_r")
    # plt.show()

    # reprocessed MARSIS data should be bottom two rgrams
    dat = dat[-(rdata.snum*rdata.nchan):,:]

    # reshape into stacked 3D array for two channels
    rdata.dat = np.zeros((rdata.snum,rdata.tnum,rdata.nchan))
    rdata.dat[:,:,0] = dat[:rdata.snum,:]
    rdata.dat[:,:,1] = dat[-rdata.snum:,:]
    # apparently data arrays are already power values, so revert to amplitude (abs(amplitude))
    rdata.dat = np.sqrt(rdata.dat)
    rdata.set_proc(rdata.dat)
    
    # convert png clutter sim product to numpy array
    simpath = glob.glob(simpath + "*clutterSim_multilook_analysis*")[0]

    if os.path.isfile(simpath):
        im = imageio.imread(simpath)
        sim = np.array(im)
        sim = sim[int(rdata.snum/2):-int(rdata.snum/2),:]
    else:
        sim = np.ones(rdata.dat.shape)
    rdata.set_sim(sim)

    # open geom nav file for rgram
    geom_path = glob.glob(root + "*tab")[0]
 
    # parse nav
    rdata.navdf = navparse.getnav_marsis(geom_path, navcrs, body)

    rdata.gndElev = np.repeat(np.nan, rdata.tnum)

    # initialize surface pick
    rdata.pick.current_surf = np.repeat(np.nan, rdata.tnum)

    return rdata