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
from cycler import cycler
from scipy.interpolate import CubicSpline
try:
    plt.rcParams["font.family"] = "Times New Roman"
except:
    pass

class impick(tk.Frame):
    # initialize impick frame with variables passed from mainGUI
    def __init__(self, parent, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)
        self.parent = parent
        # variables only setup once
        self.im_status = tk.StringVar()
        self.chan = tk.IntVar()
        self.winSize = tk.IntVar(value=0)
        self.horVar = tk.StringVar()
        self.segVar = tk.IntVar()
        self.color = tk.StringVar()
        self.set_vars()
        self.setup()


    # set_vars is a method to set impick variables which need to reset upon each load
    def set_vars(self):
        self.pick_vis = True
        self.ann_vis = True
        self.basemap = None
        self.pick_surf = None
        self.popupFlag = True

        self.pick_state = False
        self.pyramid = None

        # image colormap bounds
        self.data_cmin = None
        self.data_cmax = None
        self.sim_cmin = None
        self.sim_cmax = None

        # image colormap range
        self.data_crange = None
        self.sim_crange = None

        # initialize path objects #
        self.tmp_horizon_path = path([],[])                                     # temporary path object to hold horizon segment currently being picked/edited
        self.horizon_paths = {}                                                 # dictionary to hold horizon paths for saved picks

        # initialize line objects
        self.tmp_horizon_ln = None
        self.horizon_lns = {}
        self.horizontal_line = None
        self.vertical_line = None

        # initialize list of pick annotations
        self.ann_list = []
        self.horizons = []

        # necessary flags
        self.sim_imSwitch_flag = False
        self.edit_flag = False

        self.edit_segmentNum = 0
        self.im_status.set("data")
        self.debugState = False
        self.horVar.set("")
        self.segVar.set(0)
        self.color.set("")


    # setup impick
    def setup(self):
        # set up frames
        infoFrame0 = tk.Frame(self.parent)
        infoFrame0.pack(side="top",fill="both")        
        infoFrame = tk.Frame(infoFrame0)
        infoFrame.pack(side="left",fill="both")
        interpFrame = tk.Frame(infoFrame0, width=500)
        interpFrame.pack(side="right",fill="both")
        interpFrame.pack_propagate(0)
        toolbarFrame = tk.Frame(infoFrame)
        toolbarFrame.pack(side="bottom",fill="both")
        self.dataFrame = tk.Frame(self.parent)
        self.dataFrame.pack(side="bottom", fill="both", expand=1)

        # add radio buttons for toggling between radargram and clutter sim
        radarRadio = tk.Radiobutton(infoFrame, text="Radargram", variable=self.im_status, value="data",command=self.show_data)
        radarRadio.pack(side="left")
        simRadio = tk.Radiobutton(infoFrame,text="Clutter Sim", variable=self.im_status, value="sim",command=self.show_sim)
        simRadio.pack(side="left")
        tk.ttk.Separator(infoFrame,orient="vertical").pack(side="left", fill="both", padx=10, pady=4)

        # add radio buttons for toggling data channel
        tk.Label(infoFrame, text="Channel: ").pack(side="left")
        tk.Radiobutton(infoFrame,text="0", variable=self.chan, value=0, command=self.switchChan).pack(side="left")
        tk.Radiobutton(infoFrame,text="1", variable=self.chan, value=1, command=self.switchChan).pack(side="left")
        tk.ttk.Separator(infoFrame,orient="vertical").pack(side="left", fill="both", padx=10, pady=4)

        # add entry box for peak finder window size
        tk.Label(infoFrame, text = "Amplitude Window [#Samples]: ").pack(side="left")
        tk.Entry(infoFrame, textvariable=self.winSize, width = 5).pack(side="left")
        tk.ttk.Separator(infoFrame,orient="vertical").pack(side="left", fill="both", padx=10, pady=4)

        # set up frame to hold pick information
        interpFrameT = tk.Frame(interpFrame)
        interpFrameT.pack(fill="both",expand=True)
        interpFrameT.pack_propagate(0)
        interpFrameB = tk.Frame(interpFrame)
        interpFrameB.pack(fill="both",expand=True)
        interpFrameB.pack_propagate(0)

        interpFrameTl = tk.Frame(interpFrameT,width=400,relief="ridge", borderwidth=1)
        interpFrameTl.pack(side="left",fill="both",expand=True)
        interpFrameTl.pack_propagate(0)
        interpFrameTr = tk.Frame(interpFrameT,width=100)
        interpFrameTr.pack(side="left",fill="both",expand=True)
        interpFrameTr.pack_propagate(0)

        interpFrameBl = tk.Frame(interpFrameB,width=400,relief="ridge", borderwidth=1)
        interpFrameBl.pack(side="left",fill="both",expand=True)
        interpFrameBl.pack_propagate(0)
        interpFrameBr = tk.Frame(interpFrameB,width=100)
        interpFrameBr.pack(side="left",fill="both",expand=True)
        interpFrameBr.pack_propagate(0)

        tk.Label(interpFrameTl,text="Horizon:\t").pack(side="left")
        self.horizons=[None]
        self.horMenu = tk.OptionMenu(interpFrameTl, self.horVar, *self.horizons)
        self.horMenu.pack(side="left")
        self.horMenu.config(width=20)
        self.horVar.trace("w", lambda *args, last=True : self.update_seg_opt_menu(last)) 
        self.horVar.trace("w", lambda *args, menu=self.horMenu, var="horVar" : self.set_menu_color(menu, var))
        tk.Button(interpFrameTl, text="Delete", width=4, command=lambda:self.rm_horizon(horizon=self.horVar.get(), verify=True)).pack(side="right")
        tk.Button(interpFrameTl, text="New", width=4, command=self.init_horizon).pack(side="right")

        tk.Label(interpFrameBl,text="Segment: ").pack(side="left")
        segments=[None]
        self.segMenu = tk.OptionMenu(interpFrameBl, self.segVar, *segments)
        self.segMenu.pack(side="left")
        self.segMenu.config(width=2)
        tk.Button(interpFrameBl, text="Delete", width=4, command=lambda:self.rm_segment(horizon=self.horVar.get(),seg=self.segVar.get())).pack(side="right")
        tk.Button(interpFrameBl, text="Edit", width=4, command=lambda:self.edit_segment(horizon=self.horVar.get(),seg=self.segVar.get())).pack(side="right")
        tk.Button(interpFrameBl, text="New", width=4, command=lambda:self.init_segment(horizon=self.horVar.get())).pack(side="right")
        # initialize pick state buttons
        label = tk.Label(interpFrameTr, text="Pick",justify="center")
        label.pack(fill="both",expand=True)
        f = tk.font.Font(label, label.cget("font"))
        f.configure(underline=True)
        label.configure(font=f)
        self.startbutton = tk.Button(interpFrameBr, text="Start", bg="green", fg="white", command=lambda:self.set_pickState(state=True))
        self.startbutton.pack(side="left",fill="both",expand=True)
        self.stopbutton = tk.Button(interpFrameBr, text="Stop", bg="red", fg="white", command=lambda:self.set_pickState(state=False))
        self.stopbutton.pack(side="left",fill="both",expand=True)

        # create matplotlib figure data canvas
        plt.rcParams.update({'font.size': 12})
        self.fig = mpl.figure.Figure()
        self.fig.patch.set_facecolor("#d9d9d9")
        self.dataCanvas = FigureCanvasTkAgg(self.fig, self.parent)
        self.ax = self.fig.add_subplot(1,1,1)
        self.fig.tight_layout(rect=[.02,.05,.97,1])

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

        # add axes for colormap sliders and reset button - leave invisible until rdata loaded
        self.ax_cmax = self.fig.add_axes([0.97, 0.55, 0.0075, 0.30])
        self.ax_cmin  = self.fig.add_axes([0.97, 0.18, 0.0075, 0.30])
        self.reset_ax = self.fig.add_axes([0.95625, 0.10, 0.03, 0.035])
     
        # create colormap sliders and reset button - initialize for data image
        self.s_cmin = mpl.widgets.Slider(self.ax_cmin, "Min", 0, 1, orientation="vertical")
        self.s_cmax = mpl.widgets.Slider(self.ax_cmax, "Max", 0, 1, orientation="vertical")
        self.cmap_reset_button = mpl.widgets.Button(self.reset_ax, "Reset", color="white")
        self.cmap_reset_button.on_clicked(self.cmap_reset)

        # add toolbar to plot
        self.toolbar = NavigationToolbar2Tk(self.dataCanvas, toolbarFrame)
        self.toolbar.update()

        # canvas callbacks
        self.click = self.fig.canvas.mpl_connect("button_press_event", self.onpress)
        self.unclick = self.fig.canvas.mpl_connect("button_release_event", self.onrelease)
        self.draw_cid = self.fig.canvas.mpl_connect("draw_event", self.update_bg)
        self.resize_cid = self.fig.canvas.mpl_connect("resize_event", self.drawData)
        self.mousemotion = self.fig.canvas.mpl_connect('motion_notify_event', self.on_mouse_move)

        # set custom mpl line colors - cyan, green, orange, magenta, yellow, blue, purple, brown
        self.ln_colors = {}
        self.ln_colors["str"] = ["cyan", "green", "orange", "magenta", "yellow", "blue", "purple", "brown"]
        self.ln_colors["hex"] = ["#17becf","#2ca02c","#ff7f0e","#e377c2","#bcbd22","#1f77bf","#9467bd","#8c564b"]
        self.ln_colors["used"] = {}
        mpl.rcParams['axes.prop_cycle'] = cycler(color=self.ln_colors["hex"])


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

        # plot existing subsurface pick layers
        # self.existing_subsurf_lns = []
        # count = len(self.rdata.pick.existing_twttSubsurf.items())
        # for _i in range(count):
        #     self.ax.plot(np.arange(self.rdata.tnum), utils.twtt2sample(self.rdata.pick.existing_twttSubsurf[str(_i)], self.rdata.dt),  linewidth=1)
        #     self.existing_subsurf_lns.append(self.ax.lines[_i])

        # initialize line to hold current picks
        self.tmp_horizon_ln, = self.ax.plot(self.tmp_horizon_path.x, self.tmp_horizon_path.y, "rx")
        # initialize cursor crosshair lines
        self.horizontal_line = self.ax.axhline(color="r", lw=1, ls="--")
        self.vertical_line = self.ax.axvline(color="r", lw=1, ls="--")
        self.set_cross_hair_visible(self.get_pickState())


        # plot existing surface pick horizon as cyan
        if "srf" in self.rdata.pick.horizons:
            # initialize surface path dictionary and create line object
            self.color.set("cyan")
            self.init_horizon(horizon="srf",skip_array=True)
            self.horizon_paths["srf"][0].x = utils.nonan_idx_array(self.rdata.pick.horizons["srf"])
            self.horizon_paths["srf"][0].y = self.rdata.pick.horizons["srf"]
            x,y = utils.merge_paths(self.horizon_paths["srf"])
            self.horizon_lns["srf"].set_data(x,y)
            # init 1st surface segment by default
            self.init_segment(horizon="srf")

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
        self.s_cmin.__init__(self.ax_cmin, "Min", valmin=self.s_cmin.valmin, valmax=self.s_cmin.valmax, valinit=self.s_cmin.valinit, orientation="vertical")
        self.s_cmax.__init__(self.ax_cmax, "Max", valmin=self.s_cmax.valmin, valmax=self.s_cmax.valmax, valinit=self.s_cmax.valinit, orientation="vertical")
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


    # get_pickState is a method to return the current picking state
    def get_pickState(self):
        return self.pick_state


    # return surface being picked (surface or subsurface)
    def get_pickSurf(self):
        return self.pick_surf


    # return horizon_paths
    def get_horizon_paths(self):
        return self.horizon_paths


    # return horizon colors
    def get_horizon_colors(self):
        return self.ln_colors["used"]

    
    # set tkinter menu font colors to match color name
    def set_menu_color(self, menu=None, var=None, *args):
        if var=="color":
            c = self.ln_colors["hex"][self.ln_colors["str"].index(self.color.get())]
        elif var=="horVar":
            horizon = self.horVar.get()
            if not horizon:
                return
            c = self.ln_colors["used"][horizon]
        else:
            return
        menu.config(foreground=c, activeforeground=c, highlightcolor=c)


    # init_horizon is a method to initialize new horizon objects
    def init_horizon(self, horizon=None, skip_array=False):
        if not horizon:
            # create popup window to get new horizon name and interpreatation color
            h = tk.StringVar()
            popup = tk.Toplevel(self.parent)
            popup.geometry("500x150")
            self.popupFlag = False
            popup.config(bg="#d9d9d9")
            popup.title("New Horizon")
            popup.protocol("WM_DELETE_WINDOW", lambda:self.close_popup(popup,flag=False))
            tk.Label(popup, text="Enter new horizon name:").pack(fill="both",expand=True)
            entry = tk.Entry(popup, textvar=h, justify="center")
            entry.pack(fill="both",expand=True) 
            entry.focus_set()
            # interpretation color selection dropdown - default to first unused color in self.ln_colors
            colors = [c for c in self.ln_colors["hex"] if c not in list(self.ln_colors["used"].values())]
            self.color.set(self.ln_colors["str"][self.ln_colors["hex"].index(colors[0])])
            tk.Label(popup, text="Interpretation color:").pack(fill="both", expand=True)
            dropdown = tk.OptionMenu(popup, self.color, *[None])
            dropdown["menu"].delete(0, "end")
            dropdown.config(width=20)
            dropdown.pack(fill="none", expand=True)
            self.set_menu_color(menu=dropdown, var="color")
            # trace change in self.color to self.set_menu_color
            trace = self.color.trace("w", lambda *args, menu=dropdown, var="color" : self.set_menu_color(menu, var))
            for i,(c,hex) in enumerate(zip(self.ln_colors["str"], self.ln_colors["hex"])):
                dropdown["menu"].add_command(label=c, foreground=hex, activeforeground=hex, command=tk._setit(self.color, c))
            button = tk.Button(popup, text="OK", command=lambda:self.close_popup(popup,flag=True), width=20).pack(side="left", fill="none", expand=True)
            button = tk.Button(popup, text="Cancel", command=lambda:[h.set(""), self.close_popup(popup,flag=True)], width=20).pack(side="left", fill="none", expand=True)
            # wait for window to be closed
            self.parent.wait_window(popup)
            # remove the trace
            self.color.trace_vdelete("w", trace)
            horizon = h.get()

        if self.popupFlag and horizon:
            if not skip_array:
                # ensure horizon doesn't already exist, otherwise overwrite or return
                if horizon not in self.horizon_paths:
                    self.rdata.pick.horizons[horizon] = np.repeat(np.nan, self.rdata.tnum)
                elif tk.messagebox.askyesno("Warning","Horizon name (" + horizon + ") already exists. Overwrite?") == True:
                    self.rdata.pick.horizons[horizon] = np.repeat(np.nan, self.rdata.tnum)
                else:
                    return
            self.horizon_paths[horizon] = {}
            # initialize 0th segment for new horizon
            self.init_segment(horizon=horizon)
            # initialize line object for new horizon
            x,y = utils.merge_paths(self.horizon_paths[horizon])
            self.horizon_lns[horizon], = self.ax.plot(x,y,c=self.ln_colors["hex"][self.ln_colors["str"].index(self.color.get())])            
            # update horizon and segment options
            self.update_hor_opt_menu()  
            # set horVar to new horizon
            self.horVar.set(horizon)  

        else:
            return


    # remove horizon
    def rm_horizon(self, rm_all=False, horizon=None, verify=False):
        if len(self.horizon_paths) == 0:
            return

        if rm_all:
            if tk.messagebox.askyesno("Warning","Remove all interpretation horizons?"):
                horizon = list(self.horizon_paths.keys())
            else:
                return

        if horizon:
            if verify and not tk.messagebox.askyesno("Warning","Remove " + horizon + " horizon?"):
                return
            if isinstance(horizon,str):
                horizon = [horizon]
            for h in horizon:
                # get index of key to remove annotation
                i = list(self.horizon_paths.keys()).index(h)
                self.ann_list[i].remove()
                del self.ann_list[i]
                # remove path objects, lines, and pick horizons
                self.horizon_lns[h].remove()
                del self.horizon_lns[h]
                del self.horizon_paths[h]
                del self.rdata.pick.horizons[h]
                del self.ln_colors["used"][h]
            # reset horizon and segment variables
            if len(self.horizon_paths) > 0:
                h = list(self.horizon_paths.keys())[-1]
                self.horVar.set(h)
                self.segVar.set(len(self.horizon_paths[h]))
            else:
                self.horVar.set("")
                self.segVar.set(0)
            self.update_pickLabels() 
            self.update_bg()
            self.update_hor_opt_menu()
            self.update_seg_opt_menu()
    

    # init_segment is a method to initialize new pick segment
    def init_segment(self, horizon=None):
        if horizon:
            l = len(self.horizon_paths[horizon])
            self.horizon_paths[horizon][l] = path(np.repeat(np.nan, self.rdata.tnum), np.repeat(np.nan, self.rdata.tnum))
            self.segVar.set(l)
            # update segment options
            self.update_seg_opt_menu()


    # edit selected interpretation segment
    def edit_segment(self, horizon=None, seg=None):
        # ensure segment belongs to horizon and that interpretations have been made
        if (seg in self.horizon_paths[horizon]):
            if (np.isnan(self.horizon_paths[horizon][seg].x).all()) or (self.edit_flag==True):
                return
            if not (tk.messagebox.askokcancel("Warning", "Edit interpretation segment " + horizon + "_" + str(seg) + "?", icon="warning")):
                return
            self.edit_flag = True
            # self.edit_segmentNum = layer
            self.set_pickState(True)
            # find indices of picked traces
            picks_idx = np.where(~np.isnan(self.horizon_paths[horizon][seg].x))[0]
            # return picked traces to xln list
            self.tmp_horizon_path.x = picks_idx[::50].tolist()
            # return picked samples to yln list
            self.tmp_horizon_path.y = self.horizon_paths[horizon][seg].y[self.tmp_horizon_path.x].tolist()
            # clear saved picks for horizon segment
            self.horizon_paths[horizon][seg].x[picks_idx] = np.nan
            self.horizon_paths[horizon][seg].y[picks_idx] = np.nan
            self.rdata.pick.horizons[horizon][picks_idx] = np.nan
            # reset plotted lines
            self.tmp_horizon_ln.set_data(self.tmp_horizon_path.x, self.tmp_horizon_path.y)
            x,y = utils.merge_paths(self.horizon_paths[horizon])
            self.horizon_lns[horizon].set_data(x,y)
            self.update_bg()


    # remove selected interpretation segment
    def rm_segment(self, horizon=None, seg=None):
        # ensure segment belongs to horizon and that interpretations have been made
        if (seg in self.horizon_paths[horizon]):
            if (np.isnan(self.horizon_paths[horizon][seg].x).all()) and (self.edit_flag==False):
                return
            if not (tk.messagebox.askokcancel("Warning", "Remove interpretation segment " + horizon + "_" + str(seg) + "?", icon="warning")):
                return
            # if currently editing layer, clear tmp horizon objects
            if self.edit_flag==True:
                # clear active pick lists
                del self.tmp_horizon_path.x[:]
                del self.tmp_horizon_path.y[:]
                self.tmp_horizon_ln.set_data(self.tmp_horizon_path.x, self.tmp_horizon_path.y)
                self.set_pickState(False)

            # remove horizon interpretation path object for segment
            del self.horizon_paths[horizon][seg]

            # reorder pick segments and path objects if necessary
            l = len(self.horizon_paths[horizon])
            if seg != l:
                for _i in range(seg, l):
                    self.horizon_paths[horizon][_i] = path(self.horizon_paths[horizon][_i + 1].x, self.horizon_paths[horizon][_i + 1].y)
                del self.horizon_paths[horizon][_i + 1]

            self.update_pickLabels() 
            self.update_seg_opt_menu()
            # reset line object for horizon
            x,y = utils.merge_paths(self.horizon_paths[horizon])
            self.horizon_lns[horizon].set_data(x,y)
            self.update_bg()
    

    # set_pickState is a method to handle the pick state for a given surface as well as pick labels
    def set_pickState(self, state=False):
        self.pick_state = state
        horizon = self.horVar.get()
        seg=self.segVar.get()
        # if no horizon selected, force user to create new horizon
        if not horizon:
            self.init_horizon()
        # temporary path object length
        l = len(self.tmp_horizon_path.x)                
        # handle pick state true
        if state==True:
            self.startbutton.config(relief="sunken")
            self.stopbutton.config(relief="raised")
            # temporarily disable horizon and segment menus
            self.horMenu.config(state="disabled")
            self.segMenu.config(state="disabled")
            if l == 0:
                pass
            elif l == 1:
                self.clear_last()
            else:
                self.pick_interp(horizon=horizon,seg=seg)
                self.plot_picks(horizon=horizon)
                # if subsequent segment doesn't already exist, initialize
                if (seg + 1) not in self.horizon_paths[horizon]:
                    self.init_segment(horizon)
                else:
                    self.segVar.set(seg + 1)

        # handle pick state false
        elif state==False:
            self.startbutton.config(relief="raised")
            self.stopbutton.config(relief="sunken")
            # reactivate horizon and segment menus
            self.horMenu.config(state="active")
            self.segMenu.config(state="active")
            if l >=  2:
                self.pick_interp(horizon=horizon,seg=seg)
                self.plot_picks(horizon=horizon)
                if self.edit_flag==False and (seg + 1) not in self.horizon_paths[horizon]:
                    self.init_segment(horizon)
                else:
                    self.segVar.set(seg + 1)
            # if one pick, remove
            else:
                self.clear_last()
                del self.horizon_paths[horizon][list(self.horizon_paths[horizon].keys())[-1]]
            # reset self.edit_flag
            if self.edit_flag==True:
                self.edit_flag = False
                self.segVar.set(seg + 1)
        # set crosshair visibility
        self.set_cross_hair_visible(state)
        # add pick annotations
        self.update_pickLabels()
        self.update_seg_opt_menu()
        self.update_bg()


    # addseg is a method to for user to generate picks
    def addseg(self, event):
        if self.rdata.fpath:
            # store pick trace idx as nearest integer
            pick_trace = int(round(event.xdata))
            # handle picking of last trace - don't want to round up here
            if pick_trace == self.rdata.tnum:
                pick_trace -= 1
            # store pick sample idx as nearest integer
            pick_sample = int(round(event.ydata))
            # ensure pick is within radargram bounds
            if (pick_trace < 0) or (pick_trace > self.rdata.tnum - 1) or \
                (pick_sample < 0) or (pick_sample > self.rdata.snum - 1):
                return

            # pass pick_trace to basemap
            if self.basemap and self.basemap.get_state() == 1:
                self.basemap.plot_idx(self.rdata.fn, pick_trace)

            # print pick info if in debug mode
            if self.debugState == True:
                utils.print_pickInfo(self.rdata, pick_trace, pick_sample, self.eps_r)

            # check if picking state is a go
            if self.get_pickState():
                # if pick_trace falls within other segment for horizon, return
                for path in self.horizon_paths[self.horVar.get()].values():
                    if pick_trace in path.x:
                        return

                # determine if trace already contains pick - if so, replace with current sample
                if pick_trace in self.tmp_horizon_path.x:
                    self.tmp_horizon_path.y[self.tmp_horizon_path.x.index(pick_trace)] = pick_sample

                else:
                    # if pick falls before previous pix, prepend to pick list
                    if (len(self.tmp_horizon_path.x) >= 1) and (pick_trace < self.tmp_horizon_path.x[0]):
                        self.tmp_horizon_path.x.insert(0, pick_trace)
                        self.tmp_horizon_path.y.insert(0, pick_sample)
                        self.update_pickLabels()
                        self.update_bg()

                    # if pick falls in between previous picks, insert in proper location of pick list
                    elif (len(self.tmp_horizon_path.x) >= 1) and (pick_trace > self.tmp_horizon_path.x[0]) and (pick_trace < self.tmp_horizon_path.x[-1]):
                        # find proper index to add new pick 
                        idx = utils.list_insert_idx(self.tmp_horizon_path.x, pick_trace)   
                        self.tmp_horizon_path.x = self.tmp_horizon_path.x[:idx] + [pick_trace] + self.tmp_horizon_path.x[idx:] 
                        self.tmp_horizon_path.y = self.tmp_horizon_path.y[:idx] + [pick_sample] + self.tmp_horizon_path.y[idx:] 

                    # else append new pick to end of pick list
                    else:
                        self.tmp_horizon_path.x.append(pick_trace)
                        self.tmp_horizon_path.y.append(pick_sample)
                        if len(self.tmp_horizon_path.x) == 1:
                            self.update_pickLabels()

                # set picks and draw
                self.tmp_horizon_ln.set_data(self.tmp_horizon_path.x, self.tmp_horizon_path.y)
                self.blit()


    # pick_interp is a method for cubic spline interpolation of twtt between pick locations
    def pick_interp(self, horizon=None, seg=None):
        # get current window size - handle non int entry
        try:
            winSize = self.winSize.get()  
        except:
            winSize = 0
            self.winSize.set(0) 
        # if there are at least two picked points, interpolate
        if len(self.tmp_horizon_path.x) >= 2:
            # cubic spline between picks
            cs = CubicSpline(self.tmp_horizon_path.x, self.tmp_horizon_path.y)
            # generate array between first and last pick indices on current layer
            picked_traces = np.arange(self.tmp_horizon_path.x[0], self.tmp_horizon_path.x[-1] + 1)
            sample = cs(picked_traces).astype(int)
            # if windize >=2, loop over segment and take maximum sample within window of cubic spline interp
            if winSize >= 2:
                for _i in range(len(picked_traces)):
                    sample[_i] = int(sample[_i] - (winSize/2)) + np.argmax(self.rdata.proc[int(sample[_i] - (winSize/2)):int(sample[_i] + (winSize/2)), picked_traces[_i]])
            # add pick interpolation to horizon objects for current segment
            self.horizon_paths[horizon][seg].x[picked_traces] = picked_traces
            self.horizon_paths[horizon][seg].y[picked_traces] = sample
            self.rdata.pick.horizons[horizon][picked_traces] = sample


    # plot_picks is a method to remove current pick list and add saved picks to plot
    def plot_picks(self, horizon=None):
        # remove temporary picks
        del self.tmp_horizon_path.x[:]
        del self.tmp_horizon_path.y[:]
        self.tmp_horizon_ln.set_data(self.tmp_horizon_path.x, self.tmp_horizon_path.y)
        x,y = utils.merge_paths(self.horizon_paths[horizon])
        self.horizon_lns[horizon].set_data(x,y)


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


    # clear last pick
    def clear_last(self):
        if self.pick_state == True:
            if  len(self.tmp_horizon_path.x) >= 1: 
                del self.tmp_horizon_path.x[-1:]
                del self.tmp_horizon_path.y[-1:]
                # reset self.tmp_horizon_ln, then blit
                self.tmp_horizon_ln.set_data(self.tmp_horizon_path.x, self.tmp_horizon_path.y)
                self.blit()


    # set_picks is a method to update the saved pick arrays based on the current picks
    def set_picks(self):
        # replace saved surface paths and line with updated picks
        idx = np.where(~np.isnan(self.rdata.pick.current_surf))[0]
        self.surf_saved_path = path(idx, self.rdata.pick.current_surf[idx])
        self.surf_saved_ln.set_data(self.surf_saved_path.x, self.surf_saved_path.y)
        # replace saved subsurface paths and line with updated picks
        for key, arr in self.rdata.pick.current_subsurf.items():
            idx = np.where(~np.isnan(arr))[0]
            self.subsurf_saved_path[key] = path(idx, arr[idx])
            self.horizon_lns[key].set_data(self.subsurf_saved_path[key].x, self.subsurf_saved_path[key].y)
        # update pick labels
        self.update_pickLabels()


    # update the horizon menu
    def update_hor_opt_menu(self):
        self.horizons = list(self.horizon_paths.keys())
        self.horMenu["menu"].delete(0, "end")
        for i, horizon in enumerate(self.horizons):
            c = self.horizon_lns[horizon].get_color()
            self.horMenu["menu"].add_command(label=horizon, foreground=c, activeforeground=c, command=tk._setit(self.horVar, horizon))
            # add horizon colors to ln_colors["used"] dict for use in wvpick
            self.ln_colors["used"][horizon] = c


    # update the horizon segment menu based on how many segments exist for given segment
    def update_seg_opt_menu(self, last=False, *args):
        horizon = self.horVar.get()
        self.segMenu["menu"].delete(0, "end")
        if horizon:
            for seg in sorted(self.horizon_paths[horizon].keys()):
                self.segMenu["menu"].add_command(label=seg, command=tk._setit(self.segVar, seg))
            # set segment selection to last
            if last:
                self.segVar.set(seg)


    # update_pickLabels is a method to create annotations for picks
    def update_pickLabels(self):
        for _i in self.ann_list:
            _i.remove()
        del self.ann_list[:]
        # get x and y locations for placing annotation
        # first check tmp_horizon paths
        if len(self.tmp_horizon_path.x) > 0:
            x = self.tmp_horizon_path.x[0]
            y = self.tmp_horizon_path.y[0]
            ann = self.ax.text(x-25,y+75, self.horVar.get() + "_" + str(self.segVar.get()), bbox=dict(facecolor='white', alpha=0.5), horizontalalignment='right', verticalalignment='top')
            self.ann_list.append(ann)
            if not self.ann_vis:
                ann.set_visible(False)
        for horizon, item in self.horizon_paths.items():
            for seg, path in item.items():
                x = np.where(~np.isnan(path.x))[0]
                if x.size == 0:
                    continue
                x = x[0]
                y = path.y[x]
                ann = self.ax.text(x-25,y+75, horizon + "_" + str(seg), bbox=dict(facecolor='white', alpha=0.5), horizontalalignment='right', verticalalignment='top')
                self.ann_list.append(ann)
                if not self.ann_vis:
                    ann.set_visible(False)


    def show_labels(self, vis=None):
        if vis is not None:
            self.ann_vis = vis
        if self.ann_vis:
            for _i in self.ann_list:
                _i.set_visible(True)
        else:
            for _i in self.ann_list:
                _i.set_visible(False)
        self.update_bg()


    # show_picks is a method to toggle the visibility of picks on
    def show_picks(self, vis=None):
        if vis is not None:
            self.pick_vis = vis
        self.show_artists(self.pick_vis)
        self.safe_draw()
        self.fig.canvas.blit(self.ax.bbox)


    # show plotted lines - don't override cursor crosshair visibility
    def show_artists(self,val=True,force=False):
        for _i in self.ax.lines:
            if force:
                _i.set_visible(val)
            else:
                if _i == self.horizontal_line:
                    pass
                elif _i ==self.vertical_line:
                    pass
                else:
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
        self.show_artists(False, force=True)
        self.safe_draw()
        self.axbg = self.dataCanvas.copy_from_bbox(self.ax.bbox)
        # return artists visiblity to former state
        self.show_artists(self.pick_vis,self.get_pickState())
        self.blit()


    # update the figure, without needing to redraw the "axbg" artists
    def blit(self):
        self.fig.canvas.restore_region(self.axbg)
        for _i in self.ax.lines:
            self.ax.draw_artist(_i)
        for _i in self.ann_list:
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
        if event.inaxes == self.ax:
            self.dblclick = event.dblclick
            self.time_onclick = time.time()


    # onrelease calls addseg() if the time between the button press and release events
    # is below a threshold so that segments are not drawn while trying to zoom or pan
    def onrelease(self,event):
        if event.inaxes == self.ax:
            if event.button == 1 and ((time.time() - self.time_onclick) < 0.25):
                self.addseg(event)
                # if double clicked and currently picking, end current segment
                if self.dblclick and self.get_pickState():
                    self.set_pickState(False)
            self.time_onclick = time.time()


    # set_cross_hair_visible
    def set_cross_hair_visible(self, visible):
        self.horizontal_line.set_visible(visible)
        self.vertical_line.set_visible(visible)


    # on_mouse_move blit crosshairs
    def on_mouse_move(self, event):
        # if event.inaxes == self.ax:
        x, y = event.xdata, event.ydata
        self.horizontal_line.set_ydata(y)
        self.vertical_line.set_xdata(x)
        self.ax.figure.canvas.restore_region(self.axbg)
        self.ax.draw_artist(self.horizontal_line)
        self.ax.draw_artist(self.vertical_line)
        self.blit()


    # update_figsettings
    def update_figsettings(self, figsettings):
        self.figsettings = figsettings

        plt.rcParams.update({'font.size': self.figsettings["fontsize"].get()})

        for item in ([self.ax.title, self.ax.xaxis.label, self.ax.yaxis.label, self.secaxx.xaxis.label, self.secaxy0.yaxis.label, self.secaxy1.yaxis.label] +
                    self.ax.get_xticklabels() + self.ax.get_yticklabels() + self.secaxx.get_xticklabels() + self.secaxy0.get_yticklabels() + self.secaxy1.get_yticklabels() + self.ann_list):
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
        self.set_cmap(self.figsettings["cmap"].get())
        self.fig.canvas.draw()


    # get debug state from gui settings
    def set_debugState(self, debugState):
        self.debugState = debugState


    # get eps_r setting from gui settings
    def set_eps_r(self, eps_r):
        self.eps_r = eps_r


    # export_fig is a method to receive the pick save location from gui export the radar figure
    def export_fig(self, f_saveName):
        # zoom out to full rgram extent to save pick image
        self.fullExtent()
        self.verticalClip(self.figsettings["figclip"].get())
        # temporarily turn sliders to invisible for saving image
        self.ax_cmax.set_visible(False)
        self.ax_cmin.set_visible(False)
        self.reset_ax.set_visible(False)
        self.secaxy1.set_visible(False)
        # hide pick annotations
        vis = self.ann_vis
        if vis:
            self.show_labels(vis=False)     
        # ensure picks are visible
        # self.pick_vis.set(True)
        self.show_picks(vis=True)
        w0 ,h0 = self.fig.get_size_inches()    # get pre-save figure size
        w, h = self.figsettings["figsize"].get().split(",")
        self.fig.set_size_inches((float(w),float(h)))    # set figsize to wide aspect ratio
        # hide existing picks
        # self.remove_existing_subsurf()

        # save data fig with picks
        if self.im_status.get() =="sim":
            self.show_data()
        export.fig(f_saveName, self.fig, imtype="dat")

        # save sim fig if sim exists
        if not (self.rdata.sim == 0).all():
            self.show_sim()
            # ensure picks are hidden
            # self.pick_vis.set(False)
            self.show_picks(vis=False)
            export.fig(f_saveName.rstrip(f_saveName.split("/")[-1]) + self.rdata.fn + "_sim.png", self.fig, imtype="sim")
            # self.pick_vis.set(True)
            self.show_picks(vis=True)
            self.show_data()

        # return figsize to intial values and make sliders visible again
        self.fig.set_size_inches((w0, h0))
        self.fullExtent()
        self.ax_cmax.set_visible(True)
        self.ax_cmin.set_visible(True)
        self.reset_ax.set_visible(True)
        self.secaxy1.set_visible(True)
        if vis:
            self.show_labels(True)   
        self.fig.canvas.draw()

    # close_popup
    def close_popup(self, window, flag=False):
        window.destroy()
        self.popupFlag = flag
        return


class path():
    # initialize a path object to hold x,y paths for plotting - list or array like
    def __init__(self, x=None, y=None):
        self.x = x      # x array/list
        self.y = y      # y array/list