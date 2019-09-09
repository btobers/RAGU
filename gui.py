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
        self.master.title("NOSEpick")
        self.master.protocol("WM_DELETE_WINDOW", self.close_window)
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
        self.basemapButton = Button(text = "Map", command = self.basemap)
        self.basemapButton.pack(in_=self.controls, side="left")
        # button for help message
        self.instButton = Button(self.master, text = "Help", command = self.inMsg)
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
        # self.inMsg()
        # register click and key events
        self.key = self.fig.canvas.mpl_connect("key_press_event", self.onkey)
        self.click = self.fig.canvas.mpl_connect("button_press_event", self.addseg)
        self.f_loadName = ""
        self.dtype = "amp"
        self.var_reset()
        self.open()
    
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

    def inMsg(self):
        # instructions button message box
        messagebox.showinfo("NOSEpick Instructions",
        """Nearly Optimal Subsurface Extractor:
        \n\n1. Load button to open radargram
        \n2. Click along reflector surface to pick
        \n\t\u2022<backspace> to remove the last
        \n\t\u2022<c> to remove all
        \n3. Radar and clutter buttons to toggle
        \n4. Next button to load next file
        \n5. Save button to export picks
        \n6. Map button to display basemap
        \n7. Exit button to close application""")



    def load(self):
        # method to load radar data
        print("Loading: ", self.f_loadName)
        # ingest the data
        self.data = self.igst.read(self.f_loadName)
        # set figure title
        self.ax.set_title(self.f_loadName.split("/")[-1].rstrip(".mat"))
        # find max power in data to scale image
        maxPow_data = np.nanmax(np.power(self.data[self.dtype][:],2))
        maxPow_clut = np.nanmax(np.power(self.data["clutter"][:],2))
        # scale data in dB with maxPow value as the reference
        self.imScl_data = np.log(np.power(self.data[self.dtype],2) / maxPow_data)
        self.imScl_clut = np.log(np.power(self.data["clutter"],2) / maxPow_clut)
        # cut off data at 10th percentile to avoid extreme outliers - round down
        self.mindB_data = np.floor(np.nanpercentile(self.imScl_data,10))
        self.mindB_clut = np.floor(np.nanpercentile(self.imScl_clut,10))
        # empty fields for picks
        self.xln = []
        self.yln = []
        self.pick, = self.ax.plot([],[],"r")  # empty line for current pick
        self.xln_old = []
        self.yln_old = []
        self.saved_pick, = self.ax.plot([],[],"g")  # empty line for saved pick
        # self.ax.patch.set_alpha(0)
        self.pick_x_loc = []
        self.pick_y_loc = []
        # create matplotlib figure and use imshow to display radargram
        if self.toolbar:
            # remove existing toolbar
            self.toolbar.destroy() 
        self.dataCanvas.get_tk_widget().pack(in_=self.display, side="bottom", fill="both", expand=1)      
        # display image data for radargram and clutter sim
        self.im_data  = self.ax.imshow(self.imScl_data, cmap="gray", aspect="auto", extent=[self.data["dist"][0], self.data["dist"][-1], self.data["amp"].shape[0] * self.data["dt"], 0])
        self.im_clut  = self.ax.imshow(self.imScl_clut, cmap="gray", aspect="auto", extent=[self.data["dist"][0], self.data["dist"][-1], self.data["amp"].shape[0] * self.data["dt"], 0])
        # the first time the amplitude image is loaded, update colormap to cut off values below 10th percentile
        self.im_data.set_clim([self.mindB_data, 0.0])
        self.im_clut.set_clim([self.mindB_clut, 0.0])
        # create colormap sliders and reset button - initialize for data image
        self.s_cmin = mpl.widgets.Slider(self.ax_cmin, 'min', self.mindB_data - 10, self.mindB_data + 10, valinit=self.mindB_data, orientation="vertical")
        self.s_cmax = mpl.widgets.Slider(self.ax_cmax, 'max', -10, 10, valinit=0.0, orientation="vertical")
        self.cmap_reset_button = mpl.widgets.Button(self.reset_ax, 'Reset', color="lightgoldenrodyellow")
        self.s_cmin.on_changed(self.cmap_update)
        self.s_cmax.on_changed(self.cmap_update)
        
        self.cmap_reset_button.on_clicked(self.cmap_reset)
        # set clutter sim visibility to false
        self.im_clut.set_visible(False)   

        # Save background
        self.axbg = self.dataCanvas.copy_from_bbox(self.ax.bbox)    
        # multiply y-axis label by 1e6 to plot in microseconds
        self.ax_yticks = np.round(self.ax.get_yticks()*1e6)
        self.ax.set_yticklabels(self.ax_yticks)
        self.ax.set(xlabel = "along-track distance [km]", ylabel = "two-way travel time [microsec.]")
        
        # add toolbar to plot
        self.toolbar = NavigationToolbar2Tk(self.dataCanvas, self.master)
        self.toolbar.update()
        self.dataCanvas._tkcanvas.pack()
        self.dataCanvas.draw()

