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

        # set up frames
        infoFrame = tk.Frame(self.parent)
        infoFrame.pack(side="top",fill="both")
        toolbarFrame = tk.Frame(infoFrame)
        toolbarFrame.pack(side="bottom",fill="both")
        self.dataFrame = tk.Frame(self.parent)
        self.dataFrame.pack(side="bottom", fill="both", expand=1)

        # infoFrame exists for options to be added based on optimization needs

        # create figure object and datacanvas from it
        self.fig = mpl.figure.Figure()
        self.fig.patch.set_facecolor("#d9d9d9")
        self.dataCanvas = FigureCanvasTkAgg(self.fig, self.parent)
        
        
        # add toolbar to plot
        self.toolbar = NavigationToolbar2Tk(self.dataCanvas, toolbarFrame)
        self.toolbar.update()

    # set_pickDict is a method which holds the picked layer data for optimization
    def set_pickDict(self, pickDict):
        self.pick_dict = pickDict