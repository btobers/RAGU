"""
NOSEpick - currently in development stages
created by: Brandon S. Tober and Michael S. Christoffersen
date: 25JUN19
last updated: 05SEP19
environment requirements in nose_env.yml
"""

### IMPORTS ###
import ingester
from tools import *
import os, sys, scipy
import numpy as np
import matplotlib as mpl
mpl.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from osgeo import gdal, osr
import tkinter as tk
from tkinter import Button, Frame, messagebox, Canvas, filedialog
# from PIL import ImageTk

### USER SPECIFIED VARS ###
in_path = "/mnt/Swaps/MARS/targ/supl/UAF/2018/"
map_path = "/mnt/Swaps/MARS/targ/supl/grid-AKDEM/"
test_dat_path = None#in_path + 'may/block_clutter_elev/20180523-225145.mat'

### CODE ###
class NOSEpickGUI(tk.Tk):
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
        # # add axes for colormap sliders and reset button
        # self.ax_cmax = self.fig.add_axes([0.95, 0.55, 0.01, 0.30])
        # self.ax_cmin  = self.fig.add_axes([0.95, 0.18, 0.01, 0.30])
        # self.reset_ax = self.fig.add_axes([0.94, 0.11, 0.03, 0.03])
        # self.dataCanvas.get_tk_widget().pack(in_=self.display, side="bottom", fill="both", expand=1)
        # self.dataCanvas.draw()
        # button for loading data
        self.loadButton = Button(self.master, text = "Load", command = self.load)
        self.loadButton.pack(in_=self.controls, side="left")
        # button for going to next data file
        self.nextButton = Button(self.master, text = "Next", command = self.next_file)
        self.nextButton.pack(in_=self.controls, side="left")
        # button for saving
        self.saveButton = Button(text = "Save", command = self.savePick)
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
        self.var_reset()
        self.load()
    
    def var_reset(self):
        # variable declarations
        self.pick_state = 0
        self.pick_layer = 0
        self.basemap_state = 0
        self.pick_dict = {}
        self.pick_idx = []
        self.toolbar = None
        self.pick_loc = None
        self.ax_cmax = None
        self.ax_cmin  = None
        self.reset_ax = None
        self.map_loadName = ""
        self.f_saveName = ""
        self.amp_imSwitch_flag = ""
        self.clutter_imSwitch_flag = ""

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
        # bring up dialog box for user to load data file
        self.igst = ingester.ingester("h5py")
        if test_dat_path is None:
            self.f_loadName = filedialog.askopenfilename(initialdir = in_path,title = "Select file",filetypes = (("mat files","*.mat"),("all files","*.*")))
        else:
            self.f_loadName = test_dat_path
        if self.f_loadName:
            print("Loading: ", self.f_loadName)
            self.data = self.igst.read(self.f_loadName)
            self.dtype = "amp"
            self.ax.set_title(self.f_loadName.split("/")[-1].rstrip(".mat"))
            # self.ax = self.fig.add_axes([0.0, self.data["dt"]*self.data["num_sample"], self.data["dist"][-1], self.data["dt"]*self.data["num_sample"]])
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
            self.matplotCanvas()
            # get index of selected file in directory
            self.file_path = self.f_loadName.rstrip(self.f_loadName.split("/")[-1])
            self.file_list = os.listdir(self.file_path)
            self.file_list.sort()
            for _i in range(len(self.file_list)):
                if self.file_list[_i] == self.f_loadName.split("/")[-1]:
                    self.file_index = _i

    def matplotCanvas(self):
        # create matplotlib figure and use imshow to display radargram
        if self.toolbar:
            # remove existing toolbar
            self.toolbar.destroy() 
        self.dataCanvas.get_tk_widget().pack(in_=self.display, side="bottom", fill="both", expand=1)
        # find max power in data to scale image
        maxPow = np.nanmax(np.power(self.data[self.dtype][:],2))
        imScl = np.log(np.power(self.data[self.dtype],2) / maxPow)
        maxdB = np.rint(np.nanmax(imScl))
        # mindB = np.nanmin(imScl)
        # mindB_round = int(np.ceil(mindB / 10.0)) * 10 
        # cut off data at 10th percentile to avoid extreme outliers
        mindB = np.rint(np.nanpercentile(imScl,10))
        self.im  = self.ax.imshow(imScl, cmap="gray", aspect="auto", extent=[self.data["dist"][0], self.data["dist"][-1], self.data["amp"].shape[0] * self.data["dt"], 0])

        # Save background
        self.axbg = self.dataCanvas.copy_from_bbox(self.ax.bbox)
        
        # multiply y-axis label by 1e6 to plot in microseconds
        self.ax_yticks = np.round(self.ax.get_yticks()*1e6)
        self.ax.set_yticklabels(self.ax_yticks)
        self.ax.set(xlabel = "along-track distance [km]", ylabel = "two-way travel time [microsec.]")
        # add colormap sliders - one for minimum and one for maximum bounds - also add reser button
        if self.ax_cmax:
            # remove existing color sliders
            self.ax_cmax.remove()
            self.ax_cmin.remove()
            self.reset_ax.remove()
        self.ax_cmax = self.fig.add_axes([0.95, 0.55, 0.01, 0.30])
        self.ax_cmin  = self.fig.add_axes([0.95, 0.18, 0.01, 0.30])
        self.reset_ax = self.fig.add_axes([0.94, 0.11, 0.03, 0.03])
        if self.dtype =="amp":
            if not self.amp_imSwitch_flag:
                # the first time the amplitude image is loaded, update colormap to cut off values below 10th percentile
                self.im.set_clim([mindB, maxdB])
            self.s_cmax_amp = mpl.widgets.Slider(self.ax_cmax, 'max', -10, 10, valinit=maxdB, orientation="vertical")
            self.s_cmin_amp = mpl.widgets.Slider(self.ax_cmin, 'min', mindB - 10, mindB + 10, valinit=mindB, orientation="vertical")
            self.s_cmin_amp.on_changed(self.cmap_update)
            self.s_cmax_amp.on_changed(self.cmap_update)
            self.cmap_reset_button_amp = mpl.widgets.Button(self.reset_ax, 'Reset', color="lightgoldenrodyellow")
            self.cmap_reset_button_amp.on_clicked(self.cmap_reset)
        elif self.dtype =="clutter":
            if not self.clutter_imSwitch_flag:
                # the first time the clutter image is loaded, update colormap to cut off values below 10th percentile
                self.im.set_clim([mindB, maxdB])
            self.s_cmax_clutter = mpl.widgets.Slider(self.ax_cmax, 'max', -10, 10, valinit=maxdB, orientation="vertical")
            self.s_cmin_clutter = mpl.widgets.Slider(self.ax_cmin, 'min', mindB - 10, mindB + 10, valinit=mindB, orientation="vertical")
            self.s_cmin_clutter.on_changed(self.cmap_update)
            self.s_cmax_clutter.on_changed(self.cmap_update)
            self.cmap_reset_button_clutter = mpl.widgets.Button(self.reset_ax, 'Reset', color="lightgoldenrodyellow")
            self.cmap_reset_button_clutter.on_clicked(self.cmap_reset)
        # add toolbar to plot
        self.toolbar = NavigationToolbar2Tk(self.dataCanvas, self.master)
        self.toolbar.update()
        self.dataCanvas._tkcanvas.pack()
        self.dataCanvas.draw()

    def basemap(self):
        # pull track up on dem basemap
        if self.f_loadName:
            self.map_loadName = filedialog.askopenfilename(initialdir = map_path, title = "Select file", filetypes = (("GeoTIFF files","*.tif"),("all files","*.*")))
        if self.map_loadName:
            print("Loading Basemap: ", self.map_loadName)
            try:
                # open geotiff and convert coordinate systems to get lat long of image extent
                self.basemap_ds = gdal.Open(self.map_loadName)              # open raster
                self.basemap_im = self.basemap_ds.ReadAsArray()             # read input raster as array
                self.basemap_proj = self.basemap_ds.GetProjection()         # get coordinate system of input raster
                self.basemap_proj_xform = osr.SpatialReference()
                self.basemap_proj_xform.ImportFromWkt(self.basemap_proj)
                # Get raster georeference info 
                width = self.basemap_ds.RasterXSize
                height = self.basemap_ds.RasterYSize
                gt = self.basemap_ds.GetGeoTransform()
                if gt[2] != 0 or gt[4] != 0:
                    print('Geotraaxnsform rotation!')
                    print('gt[2]:ax '+ gt[2] + '\ngt[4]: ' + gt[4])
                    sys.exit()
                # get corner locations
                minx = gt[0]
                miny = gt[3]  + height*gt[5] 
                maxx = gt[0]  + width*gt[1]
                maxy = gt[3] 
                # transform navdat to csys of geotiff   
                self.nav_transform = self.data['navdat'].transform(self.basemap_proj)  
                # make list of navdat x and y data for plotting on basemap - convert to kilometers
                self.xdat = []
                self.ydat = []
                for _i in range(len(self.nav_transform)):
                    self.xdat.append(self.nav_transform[_i].x)
                    self.ydat.append(self.nav_transform[_i].y)
                # create new window and show basemap
                self.basemap_window = tk.Toplevel(self.master)
                self.basemap_window.protocol("WM_DELETE_WINDOW", self.basemap_close)
                self.basemap_window.title("NOSEpick - Map Window")
                self.map_display = Frame(self.basemap_window)
                self.map_display.pack(side="bottom", fill="both", expand=1)
                self.map_fig = mpl.figure.Figure()
                self.map_fig_ax = self.map_fig.add_subplot(111)
                self.map_fig_ax.imshow(self.basemap_im, cmap="gray", aspect="auto", extent=[minx, maxx, miny, maxy])
                self.map_fig_ax.set(xlabel = "x [km]", ylabel = "y [km]")
                self.map_dataCanvas = FigureCanvasTkAgg(self.map_fig, self.basemap_window)
                self.map_dataCanvas.get_tk_widget().pack(in_=self.map_display, side="bottom", fill="both", expand=1)
                self.map_toolbar = NavigationToolbar2Tk(self.map_dataCanvas, self.basemap_window)
                self.map_toolbar.update()
                self.map_dataCanvas._tkcanvas.pack()
                # plot lat, lon atop basemap im
                self.map_fig_ax.plot(self.xdat,self.ydat,"k")
                # convert axes to kilometers
                self.map_xticks = self.map_fig_ax.get_xticks()*1e-3
                self.map_yticks = self.map_fig_ax.get_yticks()*1e-3
                # shift xticks and yticks if zero is not at the lower left
                if minx != 0:
                    self.map_xticks = [x + abs(min(self.map_xticks)) for x in self.map_xticks] 
                if miny != 0:
                    self.map_yticks = [y + abs(min(self.map_yticks)) for y in self.map_yticks] 
                self.map_fig_ax.set_xticklabels(self.map_xticks)
                self.map_fig_ax.set_yticklabels(self.map_yticks)
                # zoom in to 100 km from track on all sides
                self.map_fig_ax.set(xlim = ((min(self.xdat)- 100000),(max(self.xdat)+ 100000)), ylim = ((min(self.ydat)- 100000),(max(self.ydat)+ 100000)))
                # annotate each end of the track
                self.map_fig_ax.plot(self.xdat[0],self.ydat[0],'go',label='start')
                self.map_fig_ax.plot(self.xdat[-1],self.ydat[-1],'ro',label='end')
                self.map_fig_ax.legend()                
                self.map_dataCanvas.draw()
                self.basemap_state = 1
                
            except Exception as err:
                print("basemap load error: " + str(err))
                pass

    def picking(self):
        # change status of pick_state based on button click
        if self.f_loadName:
            if self.pick_state == 0:
                self.pick_state = 1
                self.pick_dict["layer_" + str(self.pick_layer)] = np.ones(self.data["num_trace"])*-1
                self.pickButton.configure(fg = "red")
            elif self.pick_state == 1:
                self.pick_state = 0
                self.pick_layer += 1
                # save picked lines to old variable and clear line variables
                self.xln_old.extend(self.xln)
                self.yln_old.extend(self.yln)
                del self.xln[:]
                del self.yln[:]
                # plot saved pick in green
                self.pick.set_data(self.xln, self.yln)
                self.saved_pick.set_data(self.xln_old, self.yln_old)
                self.fig.canvas.draw()
                self.pickButton.configure(fg = "green")

    def addseg(self, event):
        # add line segments with user input
        # find nearest index to event.xdata for plotting on basemap and for linearly interpolating twtt between points
        pick_idx_1 = find_nearest(self.data["dist"], event.xdata)
        # check if picking state is a go
        if self.pick_state == 1:
            if (event.inaxes != self.ax):
                return
            self.xln.append(event.xdata)
            self.yln.append(event.ydata)
            num_pick = len(self.xln)
            if num_pick >= 2:
                # if there are at least two picked points, find range of all trace numbers within their range
                pick_idx_0 = find_nearest(self.data["dist"], self.xln[-2])
                self.pick_dict["layer_" + str(self.pick_layer)][pick_idx_0] = self.yln[-2]
                self.pick_dict["layer_" + str(self.pick_layer)][pick_idx_1] = self.yln[-1]
                self.pick_idx = np.arange(pick_idx_0,pick_idx_1 + 1)
                # linearly interpolate twtt values between pick points at idx_0 and idx_1
                self.pick_dict["layer_" + str(self.pick_layer)][self.pick_idx] = np.interp(self.pick_idx, [pick_idx_0,pick_idx_1], [self.yln[-2],self.yln[-1]])
            
            # Redraw pick quickly with blitting
            self.pick.set_data(self.xln, self.yln)
            self.dataCanvas.restore_region(self.axbg)
            self.ax.draw_artist(self.pick)
            self.dataCanvas.blit(self.ax.bbox)

        if self.map_loadName:
            # basemap open, plot picked location regardless of picking state
            if self.basemap_state == 1:
                # plot pick location on basemap
                if self.pick_loc:
                    self.pick_loc.remove()
                self.pick_loc = self.map_fig_ax.scatter(self.xdat[pick_idx_1],self.ydat[pick_idx_1],c="w",marker="x",zorder=3)
                self.map_fig.canvas.draw()

    def onkey(self, event):
        # on-key commands
        if event.key =="c":
            # clear the drawing of line segments
            self.clear_picks()
        elif event.key =="backspace":
            # remove last segment
            self.clear_last()
        elif event.key =="escape":
            self.close_window()
    
    def savePick(self):
        # save picks
        if len(self.xln_old) > 0 and self.save_warning() is True:
            self.f_saveName = filedialog.asksaveasfilename(initialdir = "./",title = "Save As",filetypes = (("comma-separated values","*.csv"),))
            if self.f_saveName:
                v_ice = 3e8/np.sqrt(3.15)
                lon = []
                lat = []
                elev_air = []
                twtt_surf = []
                twtt_bed = []
                thick = []
                # get necessary data from radargram for pick locations
                # iterate through pick_dict layers
                num_pic_lyr = self.pick_layer
                for _i in range(num_pic_lyr):
                    num_pt = len(np.where(self.pick_dict["layer_" + str(_i)] != -1)[0])
                    pick_idx = np.where(self.pick_dict["layer_" + str(_i)] != -1)[0]
                    for _j in range(num_pt):
                        lon.append(self.data["navdat"][pick_idx[_j]].x)
                        lat.append(self.data["navdat"][pick_idx[_j]].y)
                        elev_air.append(self.data["navdat"][pick_idx[_j]].z)
                        twtt_surf.append(self.data["twtt_surf"][pick_idx[_j]])
                        twtt_bed.append(self.pick_dict["layer_" + str(_i)][pick_idx[_j]])
                        thick.append(((twtt_bed[_j]-twtt_surf[_j])*v_ice)/2)
                header = "lon,lat,elev_air,twtt_surf,twtt_bed,thick"
                np.savetxt(self.f_saveName, np.column_stack((np.asarray(lon),np.asarray(lat),np.asarray(elev_air),np.asarray(twtt_surf),np.asarray(twtt_bed),np.asarray(thick))), delimiter=",", newline="\n", fmt="%.8f", header=header, comments="")
                print("Picks exported: ", self.f_saveName)

    def clear_picks(self):
        # clear all picks
        if len(self.xln) and messagebox.askokcancel("Warning", "Clear all picks?", icon = "warning") == True:
            del self.xln[:]
            del self.yln[:]
            self.pick.set_data(self.xln, self.yln)
            self.fig.canvas.draw()

    def clear_last(self):
        # clear last pick
        if len(self.xln) and len(self.yln) > 0:
            del self.xln[-1:]
            del self.yln[-1:]
            self.pick.set_data(self.xln, self.yln)
            self.fig.canvas.draw()

    def next_file(self):
        # load next data file in directory
        if self.f_loadName:
            self.file_index += 1
            # save pick warning
            if self.save_warning() is True:
                if self.file_index <= (len(self.file_list) - 1):
                    self.f_loadName = (self.file_path + self.file_list[self.file_index])
                    print("Loading: ", self.f_loadName)
                    self.data = self.igst.read(self.f_loadName)
                    self.dtype = "amp"
                    del self.xln[:]
                    del self.yln[:]
                    del self.xln_old[:]
                    del self.yln_old[:]
                    self.var_reset()
                    self.matplotCanvas()
                else:
                    print("Note: " + self.f_loadName.split("/")[-1] + " is the last file in " + self.file_path)

    def show_radar(self):
        # toggle to radar data
        if self.dtype == "clutter":
            self.dtype = "amp"
            self.clutterButton.config(relief="raised")
            self.radarButton.config(relief="sunken")
            self.amp_imSwitch_flag is True
            self.im.remove()
            self.matplotCanvas()

    def show_clutter(self):
        # toggle to clutter sim
        if self.dtype == "amp":
            self.dtype = "clutter"
            self.radarButton.config(relief="raised")
            self.clutterButton.config(relief="sunken")
            self.clutter_imSwitch_flag is True
            self.im.remove()
            self.matplotCanvas()

    def cmap_update(self, s=None):
        if self.dtype =="amp":
            try:
                _cmin = self.s_cmin_amp.val
                _cmax = self.s_cmax_amp.val
                self.im.set_clim([_cmin, _cmax])
                self.fig.canvas.draw()
            except Exception as err:
                print("cmap_update error: " + str(err))
        if self.dtype =="clutter":
            try:
                _cmin = self.s_cmin_clutter.val
                _cmax = self.s_cmax_clutter.val
                self.im.set_clim([_cmin, _cmax])
                self.fig.canvas.draw()
            except Exception as err:
                print("cmap_update error: " + str(err))

    def cmap_reset(self, event):
        if self.dtype =="amp":
            self.s_cmin_amp.reset()
            self.s_cmax_amp.reset()
        elif self.dtype =="clutter":
            self.s_cmin_clutter.reset()
            self.s_cmax_clutter.reset()

    def close_window(self):
        # destroy canvas
        # first check if picks have been made and saved
        if len(self.xln) > 0 and self.f_saveName == "":
            if messagebox.askokcancel("Warning", "Exit NOSEpick without saving picks?", icon = "warning") == True:
                self.master.destroy()
        else:
            self.master.destroy()

    def save_warning(self):
        # warning to save picks before loading next file
        # first check if picks have been made and saved
        if len(self.xln) > 0 and self.f_saveName == "":
            if messagebox.askokcancel("Warning", "Load next track without saving picks?", icon = "warning") == True:
                # clear picks
                self.clear_picks()
                return True
        else: 
            return True

    def basemap_close(self):
        # close the basemap window and set state
        self.basemap_window.destroy()
        self.basemap_state = 0

### INITIALIZE ###
root = tk.Tk()
# get screen size - open root window half screen
w, h = root.winfo_screenwidth(), root.winfo_screenheight()
root.geometry("%dx%d+0+0" % (.5*w, .5*h))
# call the NOSEpickGUI class
gui = NOSEpickGUI(root)
root.mainloop()