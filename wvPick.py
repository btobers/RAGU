import utils
import numpy as np
import tkinter as tk
import sys,os,time
import matplotlib as mpl
mpl.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

class wvPick(tk.Frame):
    # wvPick is a class to optimize the picking of horizons from radar data
    def __init__(self, parent, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)
        self.parent = parent

        # set up variables
        self.winSize = tk.IntVar(value=20)
        self.stepSize = tk.IntVar(value=50)

        # set up frames
        infoFrame = tk.Frame(self.parent)
        infoFrame.pack(side="top",fill="both")
        toolbarFrame = tk.Frame(infoFrame)
        toolbarFrame.pack(side="bottom",fill="both")
        self.dataFrame = tk.Frame(self.parent)
        self.dataFrame.pack(side="bottom", fill="both", expand=1)

        # infoFrame exists for options to be added based on optimization needs
        windowLabel = tk.Label(infoFrame, text = "window size [#samples]").pack(side="left")
        windowEntry = tk.Entry(infoFrame, textvariable=self.winSize, width = 5).pack(side="left")
        stepLabel = tk.Label(infoFrame, text = "\tstep size [#traces]").pack(side="left")
        stepEntry = tk.Entry(infoFrame, textvariable=self.stepSize, width = 5).pack(side="left")
        tk.Label(infoFrame, text="\t").pack(side="left")
        stepButton = tk.Button(infoFrame, text="→", command = self.traceStep, pady=0).pack(side="left")

        # create figure object and datacanvas from it
        self.fig = mpl.figure.Figure()
        self.fig.patch.set_facecolor("#d9d9d9")
        self.dataCanvas = FigureCanvasTkAgg(self.fig, self.parent)
        self.dataCanvas.get_tk_widget().pack(in_=self.dataFrame, side="bottom", fill="both", expand=1) 

        
        # add toolbar to plot
        self.toolbar = NavigationToolbar2Tk(self.dataCanvas, toolbarFrame)
        self.toolbar.update()

        # create the figure axes
        self.ax = self.fig.add_subplot(111)
        self.ax.set_visible(False)
        self.ax.set_title('decibels')

        # update the canvas
        self.dataCanvas._tkcanvas.pack()
        self.dataCanvas.draw()

    # set_data is a method to receive the radar data
    def set_data(self, amp, dt, num_sample):
        self.data_amp = amp
        self.dt = dt
        self.num_sample = num_sample
        self.data_dB = 20*np.log10(amp)


    # set_pickDict is a method which holds the picked layer data for optimization
    def set_pickDict(self, pickDict):
        self.pick_dict = pickDict
        # determine number of pick layers
        self.num_pkLyrs = len(self.pick_dict)
        # determine which traces in layer have picks and get twtt to picks
        # self.picked_traces = np.where(self.pick_dict != -1)
        print(self.pick_dict["layer_0"][np.where(self.pick_dict["layer_0"] != -1.)[0][0]]*1e-6)

    # plot_wv is a method to draw the waveform on the datacanvas
    def plot_wv(self):
        self.ax.set_visible(True)
        self.ax.plot(self.data_dB[:,(np.where(self.pick_dict["layer_0"] != -1.)[0][0])])
        # get sample index of pick for given trace
        pick_idx = utils.find_nearest((np.arange(0,self.num_sample + 1)*self.dt), (self.pick_dict["layer_0"][np.where(self.pick_dict["layer_0"] != -1.)[0][0]]*1e-6))
        self.ax.axvline(x = pick_idx, color='r')
        self.dataCanvas.draw()

    def traceStep(self):
        print('step')

