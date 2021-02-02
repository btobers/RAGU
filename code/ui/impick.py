# RAGU - Radar Analysis Graphical Utility
#
# copyright © 2020 btobers <tobers.brandon@gmail.com>
#
# distributed under terms of the GNU GPL3.0 license
"""
impick class is a tkinter frame which handles the RAGU profile view and radar data picking
"""
### imports ###
from tools import utils, export
from ui import basemap
import numpy as np
import tkinter as tk
import sys,os,time,fnmatch,copy
import matplotlib as mpl
mpl.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.widgets import Cursor
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from scipy.interpolate import CubicSpline
try:
    plt.rcParams["font.family"] = "Times New Roman"
except:
    pass

class impick(tk.Frame):
    # initialize impick frame with variables passed from mainGUI
    def __init__(self, parent, figsettings, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)
        self.parent = parent
        self.figsettings = figsettings
        self.setup()


    # setup is a method which initialized the tkinter frame 
    def setup(self):
        # set up frames
        infoFrame = tk.Frame(self.parent)
        infoFrame.pack(side="top",fill="both")
        toolbarFrame = tk.Frame(infoFrame)
        toolbarFrame.pack(side="bottom",fill="both")
        self.dataFrame = tk.Frame(self.parent)
        self.dataFrame.pack(side="bottom", fill="both", expand=1)

        self.im_status = tk.StringVar()
        # add radio buttons for toggling between radargram and clutter sim
        radarRadio = tk.Radiobutton(infoFrame, text="radargram", variable=self.im_status, value="data",command=self.show_data)
        radarRadio.pack(side="left")
        simRadio = tk.Radiobutton(infoFrame,text="clutter sim", variable=self.im_status, value="sim",command=self.show_sim)
        simRadio.pack(side="left")
        tk.ttk.Separator(infoFrame,orient="vertical").pack(side="left", fill="both", padx=10, pady=4)

        # add radio buttons for toggling pick visibility
        self.chan = tk.IntVar()
        tk.Label(infoFrame, text="channel: ").pack(side="left")
        tk.Radiobutton(infoFrame,text="0", variable=self.chan, value=0, command=self.switchChan).pack(side="left")
        tk.Radiobutton(infoFrame,text="1", variable=self.chan, value=1, command=self.switchChan).pack(side="left")
        tk.ttk.Separator(infoFrame,orient="vertical").pack(side="left", fill="both", padx=10, pady=4)

        # add radio buttons for toggling pick visibility
        self.pick_vis = tk.BooleanVar()
        tk.Label(infoFrame, text="pick visibility: ").pack(side="left")
        tk.Radiobutton(infoFrame,text="on", variable=self.pick_vis, value=True, command=self.show_picks).pack(side="left")
        tk.Radiobutton(infoFrame,text="off", variable=self.pick_vis, value=False, command=self.show_picks).pack(side="left")
        tk.ttk.Separator(infoFrame,orient="vertical").pack(side="left", fill="both", padx=10, pady=4)

        # add radio buttons for toggling pick labels
        self.pick_ann_vis = tk.BooleanVar()
        tk.Label(infoFrame, text="pick segment labels: ").pack(side="left")
        tk.Radiobutton(infoFrame,text="on", variable=self.pick_ann_vis, value=True, command=self.show_pickLabels).pack(side="left")
        tk.Radiobutton(infoFrame,text="off", variable=self.pick_ann_vis, value=False, command=self.show_pickLabels).pack(side="left")
        tk.ttk.Separator(infoFrame,orient="vertical").pack(side="left", fill="both", padx=10, pady=4)

        tk.Button(infoFrame, text="edit", command=self.edit_pkSeg).pack(side="right")
        tk.Button(infoFrame, text="delete", command=self.delete_pkSeg).pack(side="right")

        # initialize pick segment vars with dropdown menu
        self.segVar = tk.IntVar()
        self.segments=[None]
        self.segMenu = tk.OptionMenu(infoFrame, self.segVar, *self.segments)
        self.segMenu.pack(side="right",pady=0)
        tk.Label(infoFrame,text="subsurface pick segment: ").pack(side="right")

        self.pickLabel = tk.Label(toolbarFrame, font= "Verdana 10")
        self.pickLabel.pack(side="right")
        tk.Label(toolbarFrame, text="\t").pack(side="right")
        tk.ttk.Separator(infoFrame,orient="vertical").pack(side="right", fill="both", padx=10, pady=4)

        # add entry box for peak finder window size
        self.winSize = tk.IntVar(value=0)
        tk.Entry(infoFrame, textvariable=self.winSize, width = 5).pack(side="right")
        tk.Label(infoFrame, text = "window size [#samples]: ").pack(side="right")
        tk.ttk.Separator(infoFrame,orient="vertical").pack(side="right", fill="both", padx=10, pady=4)

        # create matplotlib figure data canvas
        plt.rcParams.update({'font.size': str(self.figsettings["fontsize"].get())})
        self.fig = mpl.figure.Figure()
        self.fig.patch.set_facecolor("#d9d9d9")
        self.dataCanvas = FigureCanvasTkAgg(self.fig, self.parent)
        self.ax = self.fig.add_subplot(1,1,1)

        # add axes for colormap sliders and reset button - leave invisible until rdata loaded
        self.ax_cmax = self.fig.add_axes([0.96, 0.55, 0.0075, 0.30])
        self.ax_cmin  = self.fig.add_axes([0.96, 0.18, 0.0075, 0.30])
        self.reset_ax = self.fig.add_axes([0.95125, 0.11, 0.025, 0.03])
     
        # create colormap sliders and reset button - initialize for data image
        self.s_cmin = mpl.widgets.Slider(self.ax_cmin, "min", 0, 1, orientation="vertical")
        self.s_cmax = mpl.widgets.Slider(self.ax_cmax, "max", 0, 1, orientation="vertical")
        self.cmap_reset_button = mpl.widgets.Button(self.reset_ax, "reset", color="white")
        self.cmap_reset_button.on_clicked(self.cmap_reset)

        # initiate a twin axis that shows twtt
        self.secaxy0 = self.ax.twinx()
        self.secaxy0.yaxis.set_ticks_position("right")
        self.secaxy0.yaxis.set_label_position("right")

        # initiate a twin axis that shares the same x-axis and shows approximate depth
        self.secaxy1 = self.ax.twinx()
        self.secaxy1.yaxis.set_ticks_position("left")
        self.secaxy1.yaxis.set_label_position("left")
        self.secaxy1.spines["left"].set_position(("outward", 50))

        # initiate a twin axis that shows along-track distance
        self.secaxx = self.ax.twiny()
        self.secaxx.xaxis.set_ticks_position("bottom")
        self.secaxx.xaxis.set_label_position("bottom")
        self.secaxx.spines["bottom"].set_position(("outward", 35))

        # set zorder of secondary axes to be behind main axis (self.ax)
        self.secaxx.set_zorder(-100)
        self.secaxy0.set_zorder(-100)
        self.secaxy1.set_zorder(-100)

        # add toolbar to plot
        self.toolbar = NavigationToolbar2Tk(self.dataCanvas, toolbarFrame)
        self.toolbar.update()

        # canvas callbacks
        self.click = self.fig.canvas.mpl_connect("button_press_event", self.onpress)
        self.unclick = self.fig.canvas.mpl_connect("button_release_event", self.onrelease)
        self.draw_cid = self.fig.canvas.mpl_connect("draw_event", self.update_bg)
        self.resize_cid = self.fig.canvas.mpl_connect("resize_event", self.drawData)


    # set_vars is a method to set impick variables which need to reset upon each load
    def set_vars(self):
        self.basemap = None
        self.pick_surf = None

        self.pick_state = False
        self.pick_segment = 0
        self.pyramid = None

        # image colormap bounds
        self.data_cmin = None
        self.data_cmax = None
        self.sim_cmin = None
        self.sim_cmax = None

        # image colormap range
        self.data_crange = None
        self.sim_crange = None

        # initialize lists to hold temporary picks
        self.xln_subsurf = []
        self.yln_subsurf = []
        self.xln_surf = []
        self.yln_surf = []

        # initialize list of pick annotations
        self.ann_list= []

        # initialize arrays to hold saved picks
        self.xln_surf_saved = np.array(())
        self.yln_surf_saved = np.array(())
        self.xln_subsurf_saved = np.array(())
        self.yln_subsurf_saved = np.array(())

        # initialize lines to hold picks
        self.tmp_subsurf_ln = None
        self.saved_subsurf_ln = None
        self.tmp_surf_ln = None
        self.saved_surf_ln = None

        # necessary flags
        self.sim_imSwitch_flag = False
        self.surfpkFlag = False
        self.edit_flag = False

        self.edit_segmentNum = 0
        self.im_status.set("data")
        self.pick_vis.set(True)
        self.pick_ann_vis.set(False)
        self.debugState = False
        self.pickLabel.config(fg="#d9d9d9")

        # set figure cmap
        self.set_cmap(self.figsettings["cmap"].get())


    # set image cmap
    def set_cmap(self, cmap):
        cmap = copy.copy(mpl.cm.get_cmap(cmap))
        self.cmap = mpl.cm.get_cmap(cmap)
        # set nodata value as darkest color in cmap
        nd = self.cmap(np.linspace(0,1,256))[0]
        self.cmap.set_bad(nd)


    # load calls ingest() on the data file and sets the datacanvas
    def load(self, rdata):       
        # receive the rdata
        self.rdata = rdata

        # pack the datacanvas in data frame
        self.dataCanvas.get_tk_widget().pack(in_=self.dataFrame, side="bottom", fill="both", expand=1) 
      
        # set figure title and axes labels
        self.ax.set_title(self.rdata.fn)
        self.ax.set(xlabel = "Trace", ylabel = "Sample")

        # initialize data and clutter images with np.ones - set data in drawData
        self.im_dat  = self.ax.imshow(np.ones((100,100)), aspect="auto", 
                        extent=[0, self.rdata.tnum, self.rdata.snum, 0])
        self.im_sim  = self.ax.imshow(np.ones((100,100)), aspect="auto", 
                        extent=[0, self.rdata.tnum, self.rdata.snum, 0])

        # # set clutter sim visibility to false
        self.im_sim.set_visible(False)

        # initialize arrays to hold saved picks
        self.xln_surf_saved = np.repeat(np.nan, self.rdata.tnum)
        self.yln_surf_saved = np.repeat(np.nan, self.rdata.tnum)
        self.xln_subsurf_saved = np.repeat(np.nan, self.rdata.tnum)
        self.yln_subsurf_saved = np.repeat(np.nan, self.rdata.tnum)

        # plot existing subsurface pick layers
        self.existing_subsurf_lns = []
        count = len(self.rdata.pick.existing_twttSubsurf.items())
        for _i in range(count):
            self.ax.plot(np.arange(self.rdata.tnum), utils.twtt2sample(self.rdata.pick.existing_twttSubsurf[str(_i)], self.rdata.dt), "g", linewidth=1)
            self.existing_subsurf_lns.append(self.ax.lines[_i])

        # plot existing surface pick layer
        if np.any(self.rdata.pick.existing_twttSurf):
            self.existing_surf_ln = self.ax.plot(np.arange(self.rdata.tnum), utils.twtt2sample(self.rdata.pick.existing_twttSurf, self.rdata.dt), "c", linewidth=1)

        # initialize lines to hold current pick segments
        self.tmp_surf_ln, = self.ax.plot(self.xln_surf,self.yln_surf,"mx")                          # empty line for surface pick segment
        self.saved_surf_ln, = self.ax.plot(self.xln_surf_saved, self.yln_subsurf_saved, "y")        # emplty line for saved surface pick segment
        self.tmp_subsurf_ln, = self.ax.plot(self.xln_subsurf,self.yln_subsurf,"rx")                 # empty line for current pick segment
        self.saved_subsurf_ln, = self.ax.plot(self.xln_subsurf_saved,self.yln_subsurf_saved,"g")    # empty line for saved subsurface pick

        # update the canvas
        self.dataCanvas._tkcanvas.pack()

        # connect ylim_change with event to update image pyramiding based on zoom - have to do this on load, since clear_canvas removes axis callbacks
        self.ylim_cid = self.ax.callbacks.connect("ylim_changed", self.drawData)

        # update toolbar to save axes extents
        self.toolbar.update()

        # set color range
        self.set_crange()


    # set radar and sim array bounds for setting image color limits - just doing this once based off original arrays, not pyramids
    def set_crange(self):
        # get clim bounds - take 10th percentile for min, ignore nd values
        self.mindB_data = np.floor(np.nanpercentile(self.rdata.proc,10))
        self.maxdB_data = np.nanmax(self.rdata.proc)
        # handle possible missing sim data for cmap bounds
        if (self.rdata.sim == 0).all():
            self.mindB_sim = 0
            self.maxdB_sim = 1
        else:
            self.mindB_sim = np.floor(np.nanpercentile(self.rdata.sim,10))
            self.maxdB_sim = np.nanmax(self.rdata.sim)

        # get colormap range
        self.data_crange = self.maxdB_data - self.mindB_data
        self.sim_crange = self.maxdB_sim - self.mindB_sim
        # update color limits
        self.im_dat.set_clim([self.mindB_data, self.maxdB_data])
        self.im_sim.set_clim([self.mindB_sim, self.maxdB_sim])

        # set slider bounds - use data clim values upon initial load
        self.s_cmin.valmin = self.mindB_data - (self.data_crange/2)
        self.s_cmin.valmax = self.mindB_data + (self.data_crange/2)
        self.s_cmin.valinit = self.mindB_data
        self.s_cmax.valmin = self.maxdB_data - (self.data_crange/2)
        self.s_cmax.valmax = self.maxdB_data + (self.data_crange/2)
        self.s_cmax.valinit = self.maxdB_data

        self.update_slider()


    # update clim slider bar
    def update_slider(self):
        self.ax_cmax.clear()
        self.ax_cmin.clear()
        self.s_cmin.__init__(self.ax_cmin, "min", valmin=self.s_cmin.valmin, valmax=self.s_cmin.valmax, valinit=self.s_cmin.valinit, orientation="vertical")
        self.s_cmax.__init__(self.ax_cmax, "max", valmin=self.s_cmax.valmin, valmax=self.s_cmax.valmax, valinit=self.s_cmax.valinit, orientation="vertical")
        self.s_cmin.on_changed(self.cmap_update)
        self.s_cmax.on_changed(self.cmap_update)


    # update image colormap based on slider values
    def cmap_update(self, s=None):
        try:
            if self.im_dat.get_visible():
                # apply slider values to visible image
                self.data_cmin = self.s_cmin.val
                self.data_cmax = self.s_cmax.val
                self.im_dat.set_clim([self.data_cmin, self.data_cmax])
            else:
                self.sim_cmin = self.s_cmin.val
                self.sim_cmax = self.s_cmax.val
                self.im_sim.set_clim([self.sim_cmin, self.sim_cmax])
        except Exception as err:
            print("cmap_update error: " + str(err))


    # reset sliders to initial values
    def cmap_reset(self, event):
        if self.im_dat.get_visible():
            self.s_cmin.valmin = self.mindB_data - (self.data_crange/2)
            self.s_cmin.valmax = self.mindB_data + (self.data_crange/2)
            self.s_cmin.valinit = self.mindB_data
            self.s_cmax.valmin = self.maxdB_data - (self.data_crange/2)
            self.s_cmax.valmax = self.maxdB_data + (self.data_crange/2)
            self.s_cmax.valinit = self.maxdB_data
        else:
            # if sim is displayed, change slider bounds
            self.s_cmin.valmin = self.mindB_sim - (self.sim_crange/2)
            self.s_cmin.valmax = self.mindB_sim + (self.sim_crange/2)
            self.s_cmin.valinit = self.mindB_sim
            self.s_cmax.valmin = self.maxdB_sim - (self.sim_crange/2)
            self.s_cmax.valmax = self.maxdB_sim + (self.sim_crange/2)
            self.s_cmax.valinit = self.maxdB_sim
        self.update_slider()
        self.cmap_update()


    # method to draw radar data
    def drawData(self, force=False, event=None):
        # Get data display window size in inches
        w,h = self.fig.get_size_inches()*self.fig.dpi
        # choose pyramid
        p = -1
        for i in range(len(self.rdata.dPyramid)-1, -1, -1):
            if(self.rdata.dPyramid[i].shape[0] > h):
                p = i
                break

        # set flag to detect if canvas needs redrawing
        flag = False

        # if ideal pyramid level changed, update image
        if self.pyramid != p or force:
            self.pyramid = p
            if len(self.rdata.dPyramid[self.pyramid].shape) == 3:
                self.im_dat.set_data(self.rdata.dPyramid[self.pyramid][:,:,self.chan.get()])
            else:
                self.im_dat.set_data(self.rdata.dPyramid[self.pyramid][:,:])
            self.im_sim.set_data(self.rdata.sPyramid[self.pyramid][:,:])
            flag = True

        # update cmap if necessary
        if self.im_dat.get_cmap().name != self.cmap.name:
            self.im_dat.set_cmap(self.cmap)
            self.im_sim.set_cmap(self.cmap)
            flag = True

        if flag:
            self.dataCanvas.draw()


    # set axis labels
    def set_axes(self):
        # update twtt and depth (subradar dist.)
        if self.rdata.dt < 1e-9:
            self.secaxy0.set_ylabel("TWTT [ns]")
            self.secaxy0.set_ylim(self.rdata.snum * self.rdata.dt * 1e9, 0)
        else:
            self.secaxy0.set_ylabel("TWTT [\u03BCs]")
            self.secaxy0.set_ylim(self.rdata.snum * self.rdata.dt * 1e6, 0)

        self.secaxy1.set_ylabel("Depth [m] ($\epsilon_{}$ = {})".format("r",self.eps_r))
        self.secaxy1.set_ylim(utils.twtt2depth(self.rdata.snum * self.rdata.dt, self.eps_r), 0)

        # update along-track distance
        if not np.all(np.isnan(self.rdata.navdf["dist"])) or  np.all((self.rdata.navdf["dist"] == 0)):
            self.secaxx.set_visible(True)
            # use km if distance exceeds 1 km
            if self.rdata.navdf.iloc[-1]["dist"] >= 1e3:
                self.secaxx.set_xlabel("Along-Track Distance [km]")
                self.secaxx.set_xlim(0, self.rdata.navdf.iloc[-1]["dist"]*1e-3)

            else:
                self.secaxx.set_xlabel("Along-Track Distance [m]")
                self.secaxx.set_xlim(0, self.rdata.navdf.iloc[-1]["dist"])
        
        else:
            self.secaxx.set_visible(False)


    # method to zoom to full image extent
    def fullExtent(self):
        self.ax.set_xlim(0, self.rdata.tnum)
        self.ax.set_ylim(self.rdata.snum, 0)
        self.set_axes()
        self.dataCanvas.draw()


    # method to vertically clip rgam for export
    def verticalClip(self, val=.3):
        self.ax.set_ylim(self.rdata.snum*val, 0)
        ylim2 = self.secaxy0.get_ylim()
        ylim3 = self.secaxy1.get_ylim()
        self.secaxy0.set_ylim(ylim2[0]*val,)
        self.secaxy1.set_ylim(ylim3[0]*val,)
        self.dataCanvas.draw()


    # method to pan right
    def panRight(self):
        xlim1 = self.ax.get_xlim()
        xlim2 = self.secaxx.get_xlim()
        if xlim1[1] < self.rdata.tnum:
            step1 = (xlim1[1] - xlim1[0]) / 2
            step2 = (xlim2[1] - xlim2[0]) / 2
            if (xlim1[1] + step1) > self.rdata.tnum:
                step1 = self.rdata.tnum - xlim1[1]
                step2 = self.rdata.navdf["dist"].iloc[-1]*1e-3 - xlim2[1]
            self.ax.set_xlim(xlim1[0] + step1, xlim1[1] + step1)
            self.secaxx.set_xlim(xlim2[0] + step2, xlim2[1] + step2)
            self.dataCanvas.draw()


    # method to pan left
    def panLeft(self):
        xlim1 = self.ax.get_xlim()
        xlim2 = self.secaxx.get_xlim()
        if xlim1[0] > 0:
            step1 = (xlim1[1] - xlim1[0]) / 2
            step2 = (xlim2[1] - xlim2[0]) / 2
            if (xlim1[0] - step1) < 0:
                step1 = xlim1[0]
                step2 = xlim2[0]
            self.ax.set_xlim(xlim1[0] - step1, xlim1[1] - step1)
            self.secaxx.set_xlim(xlim2[0] - step2, xlim2[1] - step2)
            self.dataCanvas.draw()


    # method to pan up
    def panUp(self):
        ylim1 = self.ax.get_ylim()
        ylim2 = self.secaxy0.get_ylim()
        ylim3 = self.secaxy1.get_ylim()
        if ylim1[1] > 0:
            step1 = (ylim1[0] - ylim1[1]) / 2
            step2 = (ylim2[0] - ylim2[1]) / 2
            step3 = (ylim3[0] - ylim3[1]) / 2
            if (ylim1[1] - step1) < 0:
                step1 = ylim1[1]
                step2 = ylim2[1]
                step3 = ylim3[1]
            self.ax.set_ylim(ylim1[0] - step1, ylim1[1] - step1)
            self.secaxy0.set_ylim(ylim1[0] - step2, ylim2[1] - step2)
            self.secaxy1.set_ylim(ylim3[0] - step3, ylim3[1] - step3)
            self.dataCanvas.draw()


    # method to pan down
    def panDown(self):
        ylim1 = self.ax.get_ylim()
        ylim2 = self.secaxy0.get_ylim()
        ylim3 = self.secaxy1.get_ylim()
        if ylim1[0] < self.rdata.snum:
            step1 = (ylim1[0] - ylim1[1]) / 2
            step2 = (ylim2[0] - ylim2[1]) / 2
            step3 = (ylim3[0] - ylim3[1]) / 2
            if (ylim1[0] + step1) > self.rdata.snum:
                step1 = self.rdata.snum - ylim1[0]
                step2 = (self.rdata.snum*self.rdata.dt) - ylim2[0]
                step3 = utils.twtt2depth(self.rdata.snum*self.rdata.dt, self.eps_r) - ylim3[0]
            self.ax.set_ylim(ylim1[0] + step1, ylim1[1] + step1)
            self.secaxy0.set_ylim(ylim1[0] + step2, ylim2[1] + step2)
            self.secaxy1.set_ylim(ylim3[0] + step3, ylim3[1] + step3)
            self.dataCanvas.draw()


    def switchChan(self):
        # check to make sure channel exists before switching
        if self.chan.get() == 1 and self.rdata.nchan < 2:
            self.chan.set(0)
            return
        elif self.chan.get() == 1 and self.rdata.nchan == 2:
            self.drawData(force=True)
        elif self.chan.get() == 0:
            self.drawData(force=True)


    # toggle to radar data
    def show_data(self):
        # get sim colormap slider values for reviewing
        self.sim_cmin = self.s_cmin.val
        self.sim_cmax = self.s_cmax.val
        # set colorbar initial values to previous values
        self.s_cmin.valinit = self.data_cmin
        self.s_cmax.valinit = self.data_cmax
        # set colorbar bounds
        self.s_cmin.valmin = self.mindB_data - (self.data_crange/2)
        self.s_cmin.valmax = self.mindB_data + (self.data_crange/2)
        self.s_cmax.valmin = self.maxdB_data - (self.data_crange/2)
        self.s_cmax.valmax = self.maxdB_data + (self.data_crange/2)
        self.update_slider()
        # reverse visilibilty
        self.im_sim.set_visible(False)
        self.im_dat.set_visible(True)
        self.im_status.set("data")
        # redraw canvas
        # self.update_bg()
        self.fig.canvas.draw()


    # toggle to sim viewing
    def show_sim(self):
        # get radar data colormap slider values for reviewing
        self.data_cmin = self.s_cmin.val
        self.data_cmax = self.s_cmax.val

        if not self.sim_imSwitch_flag:
            # if this is the first time viewing the sim, set colorbar limits to initial values
            self.s_cmin.valinit = self.mindB_sim
            self.s_cmax.valinit = self.maxdB_sim
        else: 
            # if sim has been shown before revert to previous colorbar values
            self.im_sim.set_clim([self.sim_cmin, self.sim_cmax])
            self.s_cmin.valinit = self.sim_cmin
            self.s_cmax.valinit = self.sim_cmax

        self.s_cmin.valmin = self.mindB_sim - (self.sim_crange/2)
        self.s_cmin.valmax = self.mindB_sim + (self.sim_crange/2)           
        self.s_cmax.valmin = self.maxdB_sim - (self.sim_crange/2)
        self.s_cmax.valmax = self.maxdB_sim + (self.sim_crange/2)
        self.update_slider()
        # reverse visilibilty
        self.im_dat.set_visible(False)
        self.im_sim.set_visible(True)
        # set flag to indicate that sim has been viewed for resetting colorbar limits
        self.sim_imSwitch_flag = True    
        self.im_status.set("sim")
        # redraw canvas
        # self.update_bg()
        self.fig.canvas.draw()


   # set_im is a method to set which rdata is being displayed
    def set_im(self):
        if self.im_status.get() == "data":
            self.show_sim()

        elif self.im_status.get() =="sim":
            self.show_data()


    # get_subsurfpkFlag is a method which returns true if manual subsurface picks exist, and false otherwise   
    def get_subsurfpkFlag(self):
        if len(self.xln_subsurf) + np.count_nonzero(~np.isnan(self.xln_subsurf_saved)) > 0:
            return True
        else:
            return False


    # get_surfPickFlag is a method which returns true if manual surface picks exist, and false otherwise
    def get_surfpkFlag(self):
        return self.surfpkFlag


    # set_surfPickFlag is a method which sets a boolean object for whether the surface has been picked
    def set_surfpkFlag(self,flag):
        self.surfpkFlag = flag


    # get_pickState is a method to return the current picking state
    def get_pickState(self):
        return self.pick_state


    # return surface being picked (surface or subsurface)
    def get_pickSurf(self):
        return self.pick_surf


    # set_pickState is a method to generate a new pick dictionary layer and plot the data
    def set_pickState(self, state, surf = None):
        self.pick_state = state
        self.pick_surf = surf
        if self.pick_surf == "subsurface":
            if self.pick_state == True:
                # if a layer was already being picked, advance the pick segment count to begin new layer
                if len(self.xln_subsurf) >= 2:
                    self.pick_segment += 1
                # if current subsurface pick layer has only one pick, remove
                else:
                    self.clear_last()
                self.pickLabel.config(text="subsurface pick segment " + str(self.pick_segment) + ":\t active", fg="red")
                # initialize pick index and twtt dictionaries for current picking layer
                self.rdata.pick.current_subsurf[str(self.pick_segment)] = np.repeat(np.nan, self.rdata.tnum)

            elif self.pick_state == False and self.edit_flag == False:
                if len(self.xln_subsurf) >=  2:
                    self.pick_segment += 1
                    self.pickLabel.config(text="subsurface pick segment " + str(self.pick_segment - 1) + ":\t inactive", fg="black")
                # if surface pick layer has only one pick, remove
                else:
                    self.clear_last()
                    del self.rdata.pick.current_subsurf[str(self.pick_segment)]
                    self.pickLabel.config(text="subsurface pick segment " + str(self.pick_segment) + ":\t inactive", fg="black")

            else:
                self.pickLabel.config(text="subsurface pick segment " + str(self.pick_segment - 1) + ":\t inactive", fg="black")

        elif self.pick_surf == "surface":
            if self.pick_state == True:                    
                self.pickLabel.config(text="surface pick segment:\t active", fg="red")
            elif self.pick_state == False:
                self.pickLabel.config(text="surface pick segment:\t inactive", fg="black")


    # addseg is a method to for user to generate picks
    def addseg(self, event):
        if self.rdata.fpath:
            # store pick trace idx as nearest integer
            self.pick_trace = int(round(event.xdata))
            # handle picking of last trace - don't want to round up here
            if self.pick_trace == self.rdata.tnum:
                self.pick_trace -= 1
            # store pick sample idx as nearest integer
            pick_sample = int(round(event.ydata))
            # ensure pick is within radargram bounds
            if (self.pick_trace < 0) or (self.pick_trace > self.rdata.tnum - 1) or \
                (pick_sample < 0) or (pick_sample > self.rdata.snum - 1):
                return
            # check if picking state is a go
            if self.pick_state == True:
                # restrict subsurface picks to fall below surface
                if (self.pick_surf == "subsurface"):# and ((pick_sample > self.rdata["surf_idx"][self.pick_trace]) or (np.isnan(self.rdata["surf_idx"][self.pick_trace]))):
                    # determine if trace already contains pick - if so, replace with current sample

                    if self.pick_trace in self.xln_subsurf:
                        self.yln_subsurf[self.xln_subsurf.index(self.pick_trace)] = pick_sample

                    else:
                        # if pick falls before previous pix, prepend to pick list
                        if (len(self.xln_subsurf) >= 1) and (self.pick_trace < self.xln_subsurf[0]):
                            self.xln_subsurf.insert(0, self.pick_trace)
                            self.yln_subsurf.insert(0, pick_sample)

                        # if pick falls in between previous picks, insert in proper location of pick list
                        elif (len(self.xln_subsurf) >= 1) and (self.pick_trace > self.xln_subsurf[0]) and (self.pick_trace < self.xln_subsurf[-1]):
                            # find proper index to add new pick 
                            idx = utils.list_insert_idx(self.xln_subsurf, self.pick_trace)   
                            self.xln_subsurf = self.xln_subsurf[:idx] + [self.pick_trace] + self.xln_subsurf[idx:] 
                            self.yln_subsurf = self.yln_subsurf[:idx] + [pick_sample] + self.yln_subsurf[idx:] 

                        # else append new pick to end of pick list
                        else:
                            self.xln_subsurf.append(self.pick_trace)
                            self.yln_subsurf.append(pick_sample)

                    # set self.pick data to plot pick on image
                    self.tmp_subsurf_ln.set_data(self.xln_subsurf, self.yln_subsurf)

                elif self.pick_surf == "surface":
                    # determine if trace already contains pick - if so, replace with current sample
                    if self.pick_trace in self.xln_surf:
                        self.yln_surf[self.xln_surf.index(self.pick_trace)] = pick_sample
                    
                    else:
                        # if pick falls before previous pix, prepend to pick list
                        if (len(self.xln_surf) >= 1) and (self.pick_trace < self.xln_surf[0]):
                            self.xln_surf.insert(0, self.pick_trace)
                            self.yln_surf.insert(0, pick_sample)

                        # if pick falls in between previous picks, insert in proper location of pick list
                        elif (len(self.xln_surf) >= 1) and (self.pick_trace > self.xln_surf[0]) and (self.pick_trace < self.xln_surf[-1]):
                            # find proper index to add new pick 
                            idx = utils.list_insert_idx(self.xln_surf, self.pick_trace)   
                            self.xln_surf = self.xln_surf[:idx] + [self.pick_trace] + self.xln_surf[idx:] 
                            self.yln_surf = self.yln_surf[:idx] + [pick_sample] + self.yln_surf[idx:] 

                        # else append new pick to end of pick list
                        else:
                            self.xln_surf.append(self.pick_trace)
                            self.yln_surf.append(pick_sample)

                    # set self.tmp_surf_ln data to plot pick on image
                    self.tmp_surf_ln.set_data(self.xln_surf, self.yln_surf)
                    # Set surfpkFlag to True to show that a surface pick has been made
                    self.set_surfpkFlag(True)

                self.blit()

            # pass pick trace location to basemap
            if self.basemap and self.basemap.get_state() == 1:
                self.basemap.plot_idx(self.rdata.fn, self.pick_trace)

            # if in debug state, print pick info
            if self.debugState == True:
                utils.print_pickInfo(self.rdata, self.pick_trace, pick_sample)


    # pick_interp is a method for cubic spline interpolation of twtt between pick locations
    def pick_interp(self,surf = None):
        # if there are at least two picked points, interpolate
        try:
            if surf == "subsurface":
                if len(self.xln_subsurf) >= 2:
                    # get current window size - handle non int entry
                    try:
                        winSize = self.winSize.get()  
                    except:
                        winSize = 0
                        self.winSize.set(0)             
                    # cubic spline between picks
                    cs = CubicSpline(self.xln_subsurf, self.yln_subsurf)
                    # generate array between first and last pick indices on current layer
                    picked_traces = np.arange(self.xln_subsurf[0], self.xln_subsurf[-1] + 1)
                    sample = cs(picked_traces).astype(int)
                    # if windize >=2, loop over segment and take maximum sample within window of cubic spline interp
                    if winSize >= 2:
                        for _i in range(len(picked_traces)):
                            sample[_i] = int(sample[_i] - (winSize/2)) + np.argmax(self.rdata.proc[int(sample[_i] - (winSize/2)):int(sample[_i] + (winSize/2)), picked_traces[_i]])
                    # add cubic spline output interpolation to pick dictionary - force output to integer for index of pick
                    if self.edit_flag == True:
                        self.rdata.pick.current_subsurf[str(self.segVar.get())][picked_traces] = sample
                        # add pick interpolation to saved pick array
                        self.xln_subsurf_saved[picked_traces] = picked_traces
                        self.yln_subsurf_saved[picked_traces] = sample
                        self.edit_flag = False
                    else:
                        self.rdata.pick.current_subsurf[str(self.pick_segment - 1)][picked_traces] = cs(picked_traces).astype(int)
                        # add pick interpolation to saved pick array
                        self.xln_subsurf_saved[picked_traces] = picked_traces
                        self.yln_subsurf_saved[picked_traces] = sample    

            elif surf == "surface":
                if len(self.xln_surf) >= 2:
                    # get current window size - handle non int entry
                    try:
                        winSize = self.winSize.get()  
                    except:
                        winSize = 0
                        self.winSize.set(0)    
                    # cubic spline between surface picks
                    cs = CubicSpline(self.xln_surf,self.yln_surf)
                    # generate array between first and last pick indices on current layer
                    picked_traces = np.arange(self.xln_surf[0], self.xln_surf[-1] + 1)
                    sample = cs(picked_traces).astype(int)
                    # if windize >=2, loop over segment and take maximum sample within window of cubic spline interp
                    if winSize >= 2:
                        for _i in range(len(picked_traces)):
                            sample[_i] = int(sample[_i] - (winSize/2)) + np.argmax(self.rdata.proc[int(sample[_i] - (winSize/2)):int(sample[_i] + (winSize/2)), picked_traces[_i]])
                    # input cubic spline output surface twtt array - force output to integer for index of pick
                    self.rdata.pick.current_surf[picked_traces] = sample
                    # add pick interpolation to saved pick array
                    self.xln_surf_saved[picked_traces] = picked_traces
                    self.yln_surf_saved[picked_traces] = sample

        except Exception as err:
            print("Pick interp error: " + str(err))


    # plot_picks is a method to remove current pick list and add saved picks to plot
    def plot_picks(self, surf = None):
        if surf == "subsurface":
            # remove temporary picks
            del self.xln_subsurf[:]
            del self.yln_subsurf[:]
            self.tmp_subsurf_ln.set_data(self.xln_subsurf, self.yln_subsurf)
            self.saved_subsurf_ln.set_data(self.xln_subsurf_saved, self.yln_subsurf_saved)

        elif surf == "surface":
            # remove temporary picks
            del self.xln_surf[:]
            del self.yln_surf[:]
            self.tmp_surf_ln.set_data(self.xln_surf, self.yln_surf)
            self.saved_surf_ln.set_data(self.xln_surf_saved, self.yln_surf_saved)


    # plot_existing is a method to plot existing picks
    def plot_existing(self, surf = None):
        if surf == "subsurface":
            count = len(self.rdata.pick.existing_twttSubsurf)
            n = len(self.existing_subsurf_lns)
            for _i in range(count - n):
                self.ax.plot(np.arange(self.rdata.tnum), utils.twtt2sample(self.rdata.pick.existing_twttSubsurf[str(n - _i)], self.rdata.dt), "g", linewidth=1)
                self.existing_subsurf_lns.append(self.ax.lines[-1])


    # remove_imported_picks is a method to remove any imported data file picks from the image
    def remove_existing_subsurf(self):
        for _i in self.existing_subsurf_lns:
            if _i in self.ax.lines:
                _i.remove()
        self.existing_subsurf_lns = []


    # clear all surface picks
    def clear_surfPicks(self):
        if len(self.xln_surf) + np.count_nonzero(~np.isnan(self.xln_surf_saved)) > 0:
            # set picking state to false
            if self.pick_state == True and self.pick_surf == "surface":
                self.set_pickState(False,surf="surface")
            # delete pick lists
            self.yln_surf_saved[:] = np.nan
            self.xln_surf_saved[:] = np.nan
            self.pickLabel.config(fg="#d9d9d9")

    
    # clear all subsurface picks
    def clear_subsurfPicks(self):
        if len(self.xln_subsurf) + np.count_nonzero(~np.isnan(self.xln_subsurf_saved)) > 0:
            # set picking state to false
            if self.pick_state == True and self.pick_surf == "subsurface":
                self.set_pickState(False,surf="subsurface")
            # delete pick lists
            self.yln_subsurf_saved[:] = np.nan
            self.xln_subsurf_saved[:] = np.nan
            # reset pick segment increment to 0
            self.pick_segment = 0
            self.pickLabel.config(fg="#d9d9d9")
            self.segVar.set(self.pick_segment)
            # remove pick annotations
            for _i in self.ann_list:
                _i.remove()
            del self.ann_list[:]


    # clear last pick
    def clear_last(self):
        if self.pick_state == True:
            if self.pick_surf == "subsurface" and len(self.xln_subsurf) >= 1:
                del self.xln_subsurf[-1:]
                del self.yln_subsurf[-1:]
                # reset self.pick, then blit
                self.tmp_subsurf_ln.set_data(self.xln_subsurf, self.yln_subsurf)
                self.blit()
                if len(self.xln_subsurf) >= 1:
                    self.pick_trace = self.xln_subsurf[-1]

            if self.pick_surf == "surface" and len(self.xln_surf) >= 1:
                del self.xln_surf[-1:]
                del self.yln_surf[-1:]
                # reset self.pick, then blit
                self.tmp_surf_ln.set_data(self.xln_surf, self.yln_surf)
                self.blit()
                if len(self.xln_surf) >= 1:
                    self.pick_trace = self.xln_surf[-1]
                if len(self.xln_surf) == 0:
                    self.surfpkFlag(False)


    # edit selected pick segment
    def edit_pkSeg(self):
        layer = self.segVar.get()
        if (len(self.rdata.pick.current_subsurf) > 0) and (self.edit_flag == False) and (not ((self.pick_state == True) and (self.pick_surf == "subsurface") and (layer == self.pick_segment))) and (tk.messagebox.askokcancel("warning", "edit pick segment " + str(layer) + "?", icon = "warning") == True):
            # if another subsurface pick segment is active, end segment
            if (self.pick_state == True) and (self.pick_surf == "subsurface") and (layer != self.pick_segment):
                self.set_pickState(False, surf="subsurface")
                self.pick_interp(surf = "subsurface")
                self.plot_picks(surf = "subsurface")
                self.update_option_menu()
            self.edit_flag = True
            self.edit_segmentNum = layer
            self.pick_state = True
            self.pick_surf = "subsurface"
            # find indices of picked traces
            picks_idx = np.where(~np.isnan(self.rdata.pick.current_subsurf[str(layer)]))[0]
            # return picked traces to xln list
            self.xln_subsurf = picks_idx[::100].tolist()
            # return picked samples to yln list
            self.yln_subsurf = self.rdata.pick.current_subsurf[str(layer)][picks_idx][::100].tolist()
            # clear saved picks
            self.xln_subsurf_saved[picks_idx] = np.nan
            self.yln_subsurf_saved[picks_idx] = np.nan
            self.rdata.pick.current_subsurf[str(layer)][picks_idx] = np.nan
            # reset plotted lines
            self.tmp_subsurf_ln.set_data(self.xln_subsurf, self.yln_subsurf)
            self.saved_subsurf_ln.set_data(self.xln_subsurf_saved, self.yln_subsurf_saved)
            # remove pick annotation
            self.ann_list[layer].remove()
            del self.ann_list[layer]
            # update pick label
            self.pickLabel.config(text="subsurface pick segment " + str(layer) + ":\t active", fg="red")
            self.blit()


    # delete selected pick segment
    def delete_pkSeg(self):
        layer = self.segVar.get()
        # delete selected pick segment
        if (len(self.rdata.pick.current_subsurf) > 0) and (tk.messagebox.askokcancel("warning", "delete pick segment " + str(layer) + "?", icon = "warning") == True):
            # if picking active and only one segment exists, clear all picks
            if (self.pick_state == True) and (len(self.rdata.pick.current_subsurf) == 1):
                self.clear_subsurfPicks()
                self.plot_picks(surf = "subsurface")

            else:
                if self.edit_flag == True and self.edit_segmentNum == layer:
                    # clear active pick lists
                    del self.xln_subsurf[:]
                    del self.yln_subsurf[:]
                    self.tmp_subsurf_ln.set_data(self.xln_subsurf, self.yln_subsurf)
                    self.edit_flag = False
                    self.set_pickState(False, "subsurface")

                else:
                    # get picked traces for layer
                    picks_idx = np.where(~np.isnan(self.rdata.pick.current_subsurf[str(layer)]))[0]
                    # remove picks from plot list
                    self.xln_subsurf_saved[picks_idx] = np.nan
                    self.yln_subsurf_saved[picks_idx] = np.nan
                    self.saved_subsurf_ln.set_data(self.xln_subsurf_saved ,self.yln_subsurf_saved)

                # delete pick dict layer
                del self.rdata.pick.current_subsurf[str(layer)]

                # remove pick annotation
                self.ann_list[layer].remove()
                del self.ann_list[layer]
                
                # roll back pick segment counter
                if self.pick_segment >=1:
                    self.pick_segment -= 1 

                # reorder pick segments if necessary
                if layer != len(self.rdata.pick.current_subsurf):
                    for _i in range(layer, len(self.rdata.pick.current_subsurf)):
                        self.rdata.pick.current_subsurf[str(_i)] = np.copy(self.rdata.pick.current_subsurf[str(_i + 1)])
                        # reorder annotations
                        self.ann_list[_i].set_text(str(_i))

                    del self.rdata.pick.current_subsurf[str(_i + 1)]

                if self.pick_state == True:
                    if self.edit_flag == True:
                        self.pickLabel.config(text="subsurface pick segment " + str(self.edit_segmentNum) + ":\t active", fg="red")
                    else:
                        self.pickLabel.config(text="subsurface pick segment " + str(self.pick_segment) + ":\t active", fg="red")

                elif self.pick_state == False:
                    if self.pick_segment >= 1:
                        self.pickLabel.config(text="subsurface pick segment " + str(self.pick_segment - 1) + ":\t inactive", fg="black")   
                    else:
                        self.pickLabel.config(text="subsurface pick segment " + str(self.pick_segment) + ":\t inactive", fg="#d9d9d9")
                self.segVar.set(0)
            self.update_option_menu()
            self.update_bg()


    # set_picks is a method to update the saved pick arrays based on the current picks
    def set_picks(self):
        # reset yln_saved arrays to replace with new dictionary values for replotting
        self.yln_surf_saved.fill(np.nan)
        self.yln_subsurf_saved.fill(np.nan)
        idx = np.where(~np.isnan(self.rdata.pick.current_surf))[0]
        self.xln_surf_saved[idx] = idx
        self.yln_surf_saved[idx] = self.rdata.pick.current_surf[idx]
        for _i in range(len(self.rdata.pick.current_subsurf)):
            idx = np.where(~np.isnan(self.rdata.pick.current_subsurf[str(_i)]))[0]
            self.xln_subsurf_saved[idx] = idx
            self.yln_subsurf_saved[idx] = self.rdata.pick.current_subsurf[str(_i)][idx]
        self.saved_surf_ln.set_data(self.xln_surf_saved, self.yln_surf_saved)
        self.saved_subsurf_ln.set_data(self.xln_subsurf_saved, self.yln_subsurf_saved)
        # update pick segment count
        self.pick_segment = len(self.rdata.pick.current_subsurf)
        # update pick labels
        self.add_pickLabels()


    def show_pickLabels(self):
        if self.pick_ann_vis.get() == True:
            for _i in self.ann_list:
                _i.set_visible(True)
        else:
            for _i in self.ann_list:
                _i.set_visible(False)

        self.update_bg()


    # add_pickLabels is a method to create annotations for picks
    def add_pickLabels(self):
        if len(self.ann_list) < self.pick_segment:
            # get x and y locations for placing annotation
            x = np.where(~np.isnan(self.rdata.pick.current_subsurf[str(self.pick_segment - 1)]))[0][0]
            y = self.rdata.pick.current_subsurf[str(self.pick_segment - 1)][x]
            ann = self.ax.text(x-75,y+75, str(self.pick_segment - 1), bbox=dict(facecolor='white', alpha=0.5), horizontalalignment='right', verticalalignment='top')
            self.ann_list.append(ann)
            if self.pick_ann_vis.get() == False:
                ann.set_visible(False)


    # update the pick layer menu based on how many segments exist
    def update_option_menu(self):
            menu = self.segMenu["menu"]
            menu.delete(0, "end")
            for _i in range(self.pick_segment):
                menu.add_command(label=_i,
                    command=tk._setit(self.segVar,_i))


    # show_picks is a method to toggle the visibility of picks on
    def show_picks(self):
        self.show_artists(self.pick_vis.get())
        self.safe_draw()
        self.fig.canvas.blit(self.ax.bbox)


    # show plotted lines
    def show_artists(self,val=True):
        for _i in self.ax.lines:
            _i.set_visible(val)


    # temporarily disconnect the draw_event callback to avoid recursion
    def safe_draw(self):
        canvas = self.fig.canvas
        canvas.mpl_disconnect(self.draw_cid)
        canvas.draw()
        self.draw_cid = canvas.mpl_connect("draw_event", self.update_bg)


    # when the figure is resized, hide picks, draw everything, and update the background image
    def update_bg(self, event=None):
        # temporarily hide artists
        self.show_artists(False)
        self.safe_draw()
        self.axbg = self.dataCanvas.copy_from_bbox(self.ax.bbox)
        # return artists visiblity to former state
        self.show_artists(self.pick_vis.get())
        self.blit()


    # update the figure, without needing to redraw the "axbg" artists
    def blit(self):
        self.fig.canvas.restore_region(self.axbg)
        for _i in self.ax.lines:
            self.ax.draw_artist(_i)
        self.fig.canvas.blit(self.ax.bbox)


    # clear_canvas is a method to clear the data canvas and figures to reset app
    def clear_canvas(self):
        # clearing individual axis objects seems to keep a history of these objects and causes axis limit issues when opening new track
        self.ax.cla()


    # get_basemap is a method to hold the basemap object passed from gui
    def get_basemap(self, basemap):
        self.basemap = basemap


    # onpress gets the time of the button_press_event
    def onpress(self,event):
        self.time_onclick = time.time()


    # onrelease calls addseg() if the time between the button press and release events
    # is below a threshold so that segments are not drawn while trying to zoom or pan
    def onrelease(self,event):
        if event.inaxes == self.ax:
            if event.button == 1 and ((time.time() - self.time_onclick) < 0.25):
                self.addseg(event)


    # update_figsettings
    def update_figsettings(self, figsettings):
        self.figsettings = figsettings

        self.set_cmap(self.figsettings["cmap"].get())

        for item in ([self.ax.title, self.ax.xaxis.label, self.ax.yaxis.label, self.secaxx.xaxis.label, self.secaxy0.yaxis.label, self.secaxy1.yaxis.label] +
                    self.ax.get_xticklabels() + self.ax.get_yticklabels() + self.secaxx.get_xticklabels() + self.secaxy0.get_yticklabels() + self.secaxy1.get_yticklabels()):
            item.set_fontsize(self.figsettings["fontsize"].get())

        self.ax.title.set_visible(self.figsettings["figtitle"].get())
        # update x-axes
        val = self.figsettings["figxaxis"].get()
        self.ax.xaxis.set_visible(val)
        self.secaxx.axis(self.figsettings["figxaxis"].get())
        # update y-axes
        val = self.figsettings["figyaxis"].get()
        self.ax.yaxis.set_visible(val)
        self.secaxy0.axis(val)
        self.secaxy1.axis(val)
        self.fig.canvas.draw()


    # get debug state from gui settings
    def set_debugState(self, debugState):
        self.debugState = debugState


    # get eps_r setting from gui settings
    def set_eps_r(self, eps_r):
        self.eps_r = eps_r


    # save_fig is a method to receive the pick save location from gui export the radar figure
    def save_fig(self, f_saveName):
        # zoom out to full rgram extent to save pick image
        self.fullExtent()
        self.verticalClip(self.figsettings["figclip"].get())
        # temporarily turn sliders to invisible for saving image
        self.ax_cmax.set_visible(False)
        self.ax_cmin.set_visible(False)
        self.reset_ax.set_visible(False)
        self.secaxy1.set_visible(False)
        # hide pick annotations
        self.pick_ann_vis.set(False)
        self.show_pickLabels()     
        # ensure picks are visible
        self.pick_vis.set(True)
        self.show_picks()
        w0 ,h0 = self.fig.get_size_inches()    # get pre-save figure size
        w, h = self.figsettings["figsize"].get().split(",")
        self.fig.set_size_inches((float(w),float(h)))    # set figsize to wide aspect ratio
        # hide existing picks
        # self.remove_existing_subsurf()

        # save data fig with picks
        if self.im_status.get() =="sim":
            self.show_data()
        export.im(f_saveName, self.fig, imtype="dat")

        # save sim fig if sim exists
        if not (self.rdata.sim == 0).all():
            self.show_sim()
            # ensure picks are hidden
            self.pick_vis.set(False)
            self.show_picks()
            export.im(f_saveName.rstrip(f_saveName.split("/")[-1]) + self.rdata.fn + "_sim.png", self.fig, imtype="sim")
            self.pick_vis.set(True)
            self.show_picks()
            self.show_data()

        # return figsize to intial values and make sliders visible again
        self.fig.set_size_inches((w0, h0))
        self.fullExtent()
        self.ax_cmax.set_visible(True)
        self.ax_cmin.set_visible(True)
        self.reset_ax.set_visible(True)
        self.secaxy1.set_visible(True)