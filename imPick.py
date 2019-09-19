import ingester
import utils
import basemap
import h5py
import numpy as np
import tkinter as tk
from tools import *
import sys
import matplotlib as mpl
mpl.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

class imPick:
    # imPick is a class to pick horizons from a radar image
    def __init__(self,master,display,f_loadName):
        self.master = master
        self.display=display

        self.f_loadName = f_loadName

        # blank data canvas
        self.data_imSwitch_flag = ""
        self.clut_imSwitch_flag = ""
        self.dtype = "amp"
        self.toolbar = None
        self.basemap = None
        self.pick_dict = {}
        self.pick_state = 0
        self.pick_layer = 0
        self.data_cmin = None
        self.data_cmax = None
        self.clut_cmin = None
        self.clut_cmax = None
        self.fig = mpl.figure.Figure()
        self.fig.patch.set_facecolor(self.master.cget('bg'))
        self.ax = self.fig.add_subplot(111)
        self.dataCanvas = FigureCanvasTkAgg(self.fig, self.master)
        # add axes for colormap sliders and reset button
        self.ax_cmax = self.fig.add_axes([0.95, 0.55, 0.01, 0.30])
        self.ax_cmin  = self.fig.add_axes([0.95, 0.18, 0.01, 0.30])
        self.reset_ax = self.fig.add_axes([0.935, 0.11, 0.04, 0.03])
        self.dataCanvas.get_tk_widget().pack(in_=self.display, side="bottom", fill="both", expand=1)
        self.dataCanvas.draw()
        self.key = self.fig.canvas.mpl_connect("key_press_event", self.onkey)
        self.click = self.fig.canvas.mpl_connect("button_press_event", self.addseg)
        self.load()


    def load(self):
        # method to load radar data
        print("Loading: " + self.f_loadName)
        # ingest the data
        self.igst = ingester.ingester("h5py")
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

        
        # # pass navdat to basemap class
        # basemap.basemap(self.data["navdat"])

    # picking is a method to generate a new pick dictionary layer and plot the data
    def picking(self, state):
        self.pick_state = state
        if self.pick_state == True:
            self.pick_dict["layer_" + str(self.pick_layer)] = np.ones(self.data["num_trace"])*-1
            self.xln_old.extend(self.xln)
            self.yln_old.extend(self.yln)
            print(self.xln_old)
            del self.xln[:]
            del self.yln[:]
            # plot saved pick in green
            self.pick.set_data(self.xln, self.yln)
            self.saved_pick.set_data(self.xln_old, self.yln_old)
            self.fig.canvas.draw()            
            self.pick_layer += 1
        elif self.pick_state == False:
            # save picked lines to old variable and clear line variables
            self.xln_old.extend(self.xln)
            self.yln_old.extend(self.yln)
            del self.xln[:]
            del self.yln[:]
            # plot saved pick in green
            self.pick.set_data(self.xln, self.yln)
            self.saved_pick.set_data(self.xln_old, self.yln_old)
            self.fig.canvas.draw()


    def addseg(self, event):
        # add line segments with user input
        # find nearest index to event.xdata for plotting on basemap and for linearly interpolating twtt between points
        self.pick_idx_1 = utils.find_nearest(self.data["dist"], event.xdata)
        # check if picking state is a go
        if self.pick_state == True:
            if (event.inaxes != self.ax):
                return
            self.xln.append(event.xdata)
            self.yln.append(event.ydata)
            num_pick = len(self.xln)
            if num_pick >= 2:
                # if there are at least two picked points, find range of all trace numbers within their range
                pick_idx_0 = utils.find_nearest(self.data["dist"], self.xln[-2])
                self.pick_dict["layer_" + str(self.pick_layer - 1)][pick_idx_0] = self.yln[-2]
                self.pick_dict["layer_" + str(self.pick_layer - 1)][self.pick_idx_1] = self.yln[-1]
                self.pick_idx = np.arange(pick_idx_0,self.pick_idx_1 + 1)
                # linearly interpolate twtt values between pick points at idx_0 and idx_1
                self.pick_dict["layer_" + str(self.pick_layer - 1)][self.pick_idx] = np.interp(self.pick_idx, [pick_idx_0,self.pick_idx_1], [self.yln[-2],self.yln[-1]])
            
            # redraw pick quickly with blitting
            self.pick.set_data(self.xln, self.yln)
            self.dataCanvas.restore_region(self.axbg)
            self.ax.draw_artist(self.pick)
            self.dataCanvas.blit(self.ax.bbox)
        
        # plot pick location to basemap
        if self.basemap:
            self.basemap.plot_idx(self.pick_idx_1)

    def onkey(self, event):
        # on-key commands
        if event.key =="c":
            # clear the drawing of line segments
            self.clear_picks()
        elif event.key =="backspace":
            # remove last segment
            self.clear_last()


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

    def show_radar(self):
        # toggle to radar data
        # get clutter colormap slider values for reviewing
        self.clut_cmin = self.s_cmin.val
        self.clut_cmax = self.s_cmax.val
        # set colorbar initial values to previous values
        self.s_cmin.valinit = self.data_cmin
        self.s_cmax.valinit = self.data_cmax
        # set colorbar bounds
        self.s_cmin.valmin = self.mindB_data - 10
        self.s_cmin.valmax = self.mindB_data + 10
        self.s_cmax.valmin = -10
        self.s_cmax.valmax = 10
        # reverse visilibilty
        self.im_clut.set_visible(False)
        self.im_data.set_visible(True)
        # redraw canvas
        self.fig.canvas.draw()

    def show_clutter(self):
        # toggle to clutter sim viewing
        # get radar data colormap slider values for reviewing
        self.data_cmin = self.s_cmin.val
        self.data_cmax = self.s_cmax.val
        if not self.clut_imSwitch_flag:
            # if this is the first time viewing the clutter sim, set colorbar limits to initial values
            self.s_cmin.valmin = self.mindB_clut - 10
            self.s_cmin.valmax = self.mindB_clut + 10
            self.s_cmin.valinit = self.mindB_clut
            self.s_cmax.valmin = -10
            self.s_cmax.valmax = 10
            self.s_cmax.valinit = 0
        else: 
            # if clutter has been shown before revert to previous colorbar values
            self.im_clut.set_clim([self.clut_cmin, self.clut_cmax])

        # reverse visilibilty
        self.im_data.set_visible(False)
        self.im_clut.set_visible(True)
        # set flag to indicate that clutter has been viewed for resetting colorbar limits
        self.clut_imSwitch_flag is True    
        # redraw canvas
        self.fig.canvas.draw()

    def cmap_update(self, s=None):
        # method to update image colormap based on slider values
        try:
            if self.im_data.get_visible():
                # apply slider values to visible image
                self.data_cmin = self.s_cmin.val
                self.data_cmax = self.s_cmax.val
                self.im_data.set_clim([self.data_cmin, self.data_cmax])
            else:
                self.clut_cmin = self.s_cmin.val
                self.clut_cmax = self.s_cmax.val
                self.im_clut.set_clim([self.clut_cmin, self.clut_cmax])
            self.fig.canvas.draw()
        except Exception as err:
            print("cmap_update error: " + str(err))

    def cmap_reset(self, event):
        # reset sliders to initial values
        if self.im_data.get_visible():
            print('data')
            self.s_cmin.reset()
            self.s_cmax.reset()
        else:
            print('clut')
            # if clutter is displayed, change slider bounds
            self.s_cmin.valmin = self.mindB_clut - 10
            self.s_cmin.valmax = self.mindB_clut + 10
            self.s_cmin.valinit = self.mindB_clut
            # slider max bounds will be same as for real data
            self.s_cmax.reset()

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

    # get_nav method returns the nav data       
    def get_nav(self):
        return self.data["navdat"]

    # get_idx is a method that reurns the trace index of a click event on the image
    def get_idx(self):
        return self.pick_idx_1

    # set_im is a method to set which data is being displayed
    def set_im(self, im_status):
        im_status = im_status
        if im_status == "data":
            self.show_radar()

        elif im_status =="clut":
            self.show_clutter()

    # get_basemap is a method to hold the basemap object passed from gui
    def get_basemap(self, basemap):
        self.basemap = basemap