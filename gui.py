"""
NOSEpick - currently in development stages
created by: Brandon S. Tober and Michael S. Christoffersen
date: 25JUN19
last updated: 09SEP2019
environment requirements in nose_env.yml
"""

### IMPORTS ###
import ingester
import utils
import imPick
import basemap
from tools import *
import os, sys, scipy
import numpy as np
import matplotlib as mpl
mpl.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import gdal, osr
import tkinter as tk
from tkinter import Button, Frame, messagebox, Canvas, filedialog


class gui(tk.Tk):
    def __init__(self, master):
        self.master = master
        # self.master.title("NOSEpick")
        self.master.protocol("WM_DELETE_WINDOW", imPick.imPick.close_window)
        self.setup()


    def setup(self):
        # frames for data display and UI
        self.controls = Frame(self.master)
        self.controls.pack(side="top")
        self.pickControls = Frame(self.master)
        self.pickControls.pack(side="top")
        self.switchIm = Frame(self.master)
        self.switchIm.pack(side="bottom")
        self.display = Frame(self.master)
        self.display.pack(side="bottom", fill="both", expand=1)
        # blank data canvas
        self.fig = mpl.figure.Figure()
        self.ax = self.fig.add_subplot(111)
        self.dataCanvas = FigureCanvasTkAgg(self.fig, self.master)
        # add axes for colormap sliders and reset button
        self.ax_cmax = self.fig.add_axes([0.95, 0.55, 0.01, 0.30])
        self.ax_cmin  = self.fig.add_axes([0.95, 0.18, 0.01, 0.30])
        self.reset_ax = self.fig.add_axes([0.935, 0.11, 0.04, 0.03])
        # self.dataCanvas.get_tk_widget().pack(in_=self.display, side="bottom", fill="both", expand=1)
        # self.dataCanvas.draw()
        # button for loading data
        self.openButton = Button(self.master, text = "Open", command = utils.open)
        self.opneButton.pack(in_=self.controls, side="left")
        # button for going to next data file
        self.nextButton = Button(self.master, text = "Next", command = utils.next_file)
        self.nextButton.pack(in_=self.controls, side="left")
        # button for saving
        self.saveButton = Button(text = "Save", command = utils.savePick)
        self.saveButton.pack(in_=self.controls, side="left")
        # button for basemap display
        self.basemapButton = Button(text = "Map", command = basemap.basemap)
        self.basemapButton.pack(in_=self.controls, side="left")
        # button for help message
        self.instButton = Button(self.master, text = "Help", command = utils.help)
        self.instButton.pack(in_=self.controls, side="left")
        # button for exit
        self.exitButton = Button(text = "Exit", fg = "red", command = self.close_window)
        self.exitButton.pack(in_=self.controls, side="left")
        # button for picking initiation
        self.pickButton = Button(text = "Pick", fg = "green", command = self.picking)
        self.pickButton.pack(in_=self.pickControls, side="left")
        # button for trace view
        self.traceButton = Button(text = "Trace View", command = None)
        self.traceButton.pack(in_=self.pickControls, side="left")
        # button for pick optimization
        self.pickOptButton = Button(text = "Pick Optimization", command = None)
        self.pickOptButton.pack(in_=self.pickControls, side="left")
        # button to toggle on radargram
        self.radarButton = Button(text = "radar", command = self.show_radar, relief="sunken")
        self.radarButton.pack(in_=self.switchIm, side="left")        
        # button to toggle on clutter
        self.clutterButton = Button(text = "clutter", command = self.show_clutter)
        self.clutterButton.pack(in_=self.switchIm, side="left")        
        # call information messageboxs
        # utils.help()
        # register click and key events
        self.key = self.fig.canvas.mpl_connect("key_press_event", self.onkey)
        self.click = self.fig.canvas.mpl_connect("button_press_event", self.addseg)
        self.f_loadName = ""
        self.dtype = "amp"
        self.var_reset()
        utils.open()
    
    
    def var_reset(self):
        # variable declarations
        self.pick_state = 0
        self.pick_layer = 0
        self.basemap_state = 0
        self.pick_dict = {}
        self.pick_idx = []
        self.toolbar = None
        self.pick_loc = None
        self.data_cmin = None
        self.data_cmax = None
        self.clut_cmin = None
        self.clut_cmax = None
        self.map_loadName = ""
        self.f_saveName = ""
        self.data_imSwitch_flag = ""
        self.clut_imSwitch_flag = ""