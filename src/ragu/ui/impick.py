# RAGU - Radar Analysis Graphical Utility
#
# copyright © 2020 btobers <tobers.brandon@gmail.com>
#
# distributed under terms of the GNU GPL3.0 license
"""
impick class is a tkinter frame which handles the RAGU profile view and radar data picking
"""
### imports ###
from ragu.tools import utils, export
from ragu.ui import basemap
import numpy as np
import tkinter as tk
import sys,os,time,fnmatch,copy,PIL
import matplotlib as mpl
mpl.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.widgets import Cursor
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from cycler import cycler
from scipy.interpolate import CubicSpline
# try:
#     plt.rcParams["font.family"] = "Times New Roman"
# except:
#     pass

class impick(tk.Frame):
    # initialize impick frame with variables passed from mainGUI
    def __init__(self, parent, button_tip, popup, fs):
        tk.Frame.__init__(self, parent)
        self.parent = parent
        self.button_tip = button_tip
        self.popup = popup
        # variables only setup once
        self.im_status = tk.IntVar(value=0)
        self.chan = tk.IntVar()
        self.winSize = tk.IntVar(value=0)
        self.horVar = tk.StringVar()
        self.segVar = tk.IntVar()
        self.color = tk.StringVar()
        self.setup(fs)


    # setup impick
    def setup(self, fs):
        # set up frames
        infoFrame0 = tk.Frame(self.parent)
        infoFrame0.pack(side="top",fill="both")        
        infoFrame = tk.Frame(infoFrame0)
        infoFrame.pack(side="left",fill="both")
        interpFrame = tk.Frame(infoFrame0, width=450)
        interpFrame.pack(side="right",fill="both")
        interpFrame.pack_propagate(0)
        toolbarFrame = tk.Frame(infoFrame)
        toolbarFrame.pack(side="bottom",fill="both")
        self.dataFrame = tk.Frame(self.parent)
        self.dataFrame.pack(side="bottom", fill="both", expand=1)

        # add radio buttons for toggling between radargram and clutter sim
        radarRadio = tk.Radiobutton(infoFrame, text="Radargram", variable=self.im_status, value=0, command=self.set_im)
        radarRadio.pack(side="left")
        self.button_tip(self.parent, radarRadio, "View radar profile")

        self.simRadio = tk.Radiobutton(infoFrame,text="Clutter Sim", variable=self.im_status, value=1, command=self.set_im)
        self.simRadio.pack(side="left")
        self.button_tip(self.parent, self.simRadio, "View clutter simulation")
        tk.ttk.Separator(infoFrame,orient="vertical").pack(side="left", fill="both", padx=10, pady=4)

        # add radio buttons for toggling data channel
        tk.Label(infoFrame, text="Channel: ").pack(side="left")
        button = tk.Radiobutton(infoFrame,text="0", variable=self.chan, value=0, command=self.switchChan)
        button.pack(side="left")
        self.button_tip(self.parent, button, text="Radar channel 0")
        button = tk.Radiobutton(infoFrame,text="1", variable=self.chan, value=1, command=self.switchChan)
        button.pack(side="left")
        self.button_tip(self.parent, button, text="Radar channel 1")
        tk.ttk.Separator(infoFrame,orient="vertical").pack(side="left", fill="both", padx=10, pady=4)

        # add entry box for peak finder window size
        tk.Label(infoFrame, text = "Amplitude Window [#Samples]: ").pack(side="left")
        entry = tk.Entry(infoFrame, textvariable=self.winSize, width = 5)
        entry.pack(side="left")
        self.button_tip(self.parent, entry, \
            "Pick amplitude window size. Window size (number of samples) centered on \
            manual picks from which to select maximum amplitude sample for selected trace.")
        tk.ttk.Separator(infoFrame,orient="vertical").pack(side="left", fill="both", padx=10, pady=4)

        # set up frame to hold pick information
        interpFrameT = tk.Frame(interpFrame)
        interpFrameT.pack(fill="both",expand=True)
        interpFrameT.pack_propagate(0)
        interpFrameB = tk.Frame(interpFrame)
        interpFrameB.pack(fill="both",expand=True)
        interpFrameB.pack_propagate(0)

        interpFrameTl = tk.Frame(interpFrameT,width=350,relief="ridge", borderwidth=1)
        interpFrameTl.pack(side="left",fill="both",expand=True)
        interpFrameTl.pack_propagate(0)
        interpFrameTr = tk.Frame(interpFrameT,width=100)
        interpFrameTr.pack(side="left",fill="both",expand=True)
        interpFrameTr.pack_propagate(0)

        interpFrameBl = tk.Frame(interpFrameB,width=350,relief="ridge", borderwidth=1)
        interpFrameBl.pack(side="left",fill="both",expand=True)
        interpFrameBl.pack_propagate(0)
        interpFrameBr = tk.Frame(interpFrameB,width=100)
        interpFrameBr.pack(side="left",fill="both",expand=True)
        interpFrameBr.pack_propagate(0)

        tk.Label(interpFrameTl,text="{0:<8}".format("Horizon:")).pack(side="left")
        button = tk.Button(interpFrameTl, text="Delete", width=4, command=lambda:self.rm_horizon(horizon=self.horVar.get()))
        button.pack(side="right")
        self.button_tip(self.parent, button, "Remove interpretation horion")
        button = tk.Button(interpFrameTl, text="Rename", width=4, command=lambda:self.rename_horizon(horizon=self.horVar.get()))
        button.pack(side="right")
        self.button_tip(self.parent, button, "Rename interpretation horion")
        button = tk.Button(interpFrameTl, text="New", width=4, command=self.init_horizon)
        button.pack(side="right")
        self.button_tip(self.parent, button, "New interpretation horion")
        self.horMenu = tk.OptionMenu(interpFrameTl, self.horVar, *[None])
        self.horMenu.pack(side="right")
        self.horMenu.config(width=10)
        self.horVar.trace("w", lambda *args, last=True : self.update_seg_opt_menu(last)) 
        self.horVar.trace("w", lambda *args, menu=self.horMenu, var="horVar" : self.set_menu_color(menu, var))

        tk.Label(interpFrameBl,text="{0:<8}".format("Segment:")).pack(side="left")
        button = tk.Button(interpFrameBl, text="Delete", width=4, command=lambda:self.rm_segment(horizon=self.horVar.get(),seg=self.segVar.get()))
        button.pack(side="right")
        self.button_tip(self.parent, button, "Remove interpretation segment")
        button = tk.Button(interpFrameBl, text="Edit", width=4, command=lambda:self.edit_segment(horizon=self.horVar.get(),seg=self.segVar.get()))
        button.pack(side="right")
        self.button_tip(self.parent, button, "Edit interpretation segment")    
        button = tk.Button(interpFrameBl, text="New", width=4, command=lambda:self.init_segment(horizon=self.horVar.get()))
        button.pack(side="right")
        self.button_tip(self.parent, button, "New interpretation segment")
        self.segMenu = tk.OptionMenu(interpFrameBl, self.segVar, *[None])
        self.segMenu.pack(side="right")
        self.segMenu.config(width=10)
    
        # initialize pick state buttons
        label = tk.Label(interpFrameTr, text="Pick",justify="center")
        label.pack(fill="both",expand=True)
        f = tk.font.Font(label, label.cget("font"))
        f.configure(underline=True)
        label.configure(font=f)
        self.startbutton = tk.Button(interpFrameBr, text="Start", bg="green", fg="white", command=lambda:self.set_pickState(state=True))
        self.startbutton.pack(side="left",fill="both",expand=True)
        self.button_tip(self.parent, self.startbutton, "Start picking")
        self.stopbutton = tk.Button(interpFrameBr, text="Stop", bg="red", fg="white", command=lambda:self.set_pickState(state=False))
        self.stopbutton.pack(side="left",fill="both",expand=True)
        self.button_tip(self.parent, self.stopbutton, "Stop picking")

        # create matplotlib figure data canvas
        plt.rcParams.update({'font.size': fs, 'axes.titlesize': fs})
        self.fig = mpl.figure.Figure()
        self.fig.patch.set_facecolor("#d9d9d9")
        self.dataCanvas = FigureCanvasTkAgg(self.fig, self.parent)
        self.ax = self.fig.add_subplot(1,1,1)
        self.fig.tight_layout(rect=[.05,.05,.97,1])

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
        self.s_cmin = mpl.widgets.Slider(self.ax_cmin, "Min", 0, 1, orientation="vertical", handle_style={"size":fs})
        self.s_cmax = mpl.widgets.Slider(self.ax_cmax, "Max", 0, 1, orientation="vertical", handle_style={"size":fs})
        self.cmap_reset_button = mpl.widgets.Button(self.reset_ax, "Reset", color="white")
        self.cmap_reset_button.label.set_fontsize(fs)
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
        mpl.rcParams['axes.prop_cycle'] = cycler(color=self.ln_colors["hex"])


    # set_vars is a method to set impick variables which need to reset upon each load
    def set_vars(self):
        self.pick_vis = True
        self.ann_vis = True
        self.basemap = None
        self.pick_surf = None

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
        self.tmp_horizon_path = path([],[])                                     # temporary path object to hold horizon segment currently being picked
        self.edit_path = None                                                   # temporary path object to hold horizon segment currently being edited
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

        self.im_status.set(0)
        self.debugState = False
        self.horVar.set("")
        self.segVar.set(0)
        self.color.set("")
        self.ln_colors["used"] = {}


    # set image cmap
    def set_cmap(self, cmap):
        cmap = copy.copy(mpl.cm.get_cmap(cmap))
        self.cmap = mpl.cm.get_cmap(cmap)
        # set nodata value as bottom color in cmap
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

        # set clutter sim visibility to false
        self.im_sim.set_visible(False)
        # disable im toggle if no sim
        if not self.rdata.flags.sim:
            self.simRadio.config(state="disabled")

        # initialize line to hold current picks
        self.tmp_horizon_ln, = self.ax.plot(self.tmp_horizon_path.x, self.tmp_horizon_path.y, "rx", ms=6)
        # initialize cursor crosshair lines
        self.horizontal_line = self.ax.axhline(color="r", lw=1, ls="--")
        self.vertical_line = self.ax.axvline(color="r", lw=1, ls="--")
        self.set_cross_hair_visible(self.get_pickState())

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
        self.mindB_data = np.nanpercentile(self.rdata.proc.get_curr_dB(),1)
        self.maxdB_data = np.nanpercentile(self.rdata.proc.get_curr_dB(),99)
        # self.maxdB_data = np.nanmax(self.rdata.proc.get_curr_dB())

        if self.rdata.flags.sim:
            self.mindB_sim = np.floor(np.nanpercentile(self.rdata.sim,10))
            self.maxdB_sim = np.nanmax(self.rdata.sim)
            self.sim_crange = self.maxdB_sim - self.mindB_sim
            self.im_sim.set_clim([self.mindB_sim, self.maxdB_sim])

        # get colormap range
        self.data_crange = self.maxdB_data - self.mindB_data
        # update color limits
        self.im_dat.set_clim([self.mindB_data, self.maxdB_data])

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
                # update norm
                # self.im_dat.set_norm(mpl.colors.LogNorm(self.data_cmin, self.data_cmax))
            else:
                self.sim_cmin = self.s_cmin.val
                self.sim_cmax = self.s_cmax.val
                self.im_sim.set_clim([self.sim_cmin, self.sim_cmax])
                # update norm
                # self.im_sim.set_norm(mpl.colors.LogNorm(self.sim_cmin, self.sim_cmax))
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
            if self.rdata.flags.sim:
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

        self.secaxy1.set_ylabel("Depth [m] (" + r"$\epsilon_{r}$" + f"= {self.eps_r})")
        self.secaxy1.set_ylim(utils.twtt2depth(self.rdata.snum * self.rdata.dt, np.nanmean(self.rdata.asep), self.eps_r), 0)

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
    def verticalClip(self, top=0.0, bottom = 0.5):
        self.ax.set_ylim(self.rdata.snum*bottom, self.rdata.snum*top)
        ylim2 = self.secaxy0.get_ylim()
        ylim3 = self.secaxy1.get_ylim()
        self.secaxy0.set_ylim(ylim2[0]*bottom,ylim2[0]*top)
        self.secaxy1.set_ylim(ylim3[0]*bottom,ylim3[0]*top)
        self.dataCanvas.draw()

    # method to zoom in
    def zoomIn(self, factor=1/4):
        # get original axis limits
        xlima1 = self.ax.get_xlim()
        xlima2 = self.secaxx.get_xlim()
        ylima1 = self.ax.get_ylim()
        ylima2 = self.secaxy0.get_ylim()
        ylima3 = self.secaxy1.get_ylim()

        xstep1 = abs(xlima1[1] - xlima1[0]) * factor
        xstep2 = abs(xlima2[1] - xlima2[0]) * factor
        ystep1 = abs(ylima1[1] - ylima1[0]) * factor
        ystep2 = abs(ylima2[1] - ylima2[0]) * factor
        ystep3 = abs(ylima3[1] - ylima3[0]) * factor

        # add steps
        xlimb1 = [xlima1[0]+xstep1, xlima1[1]-xstep1]
        xlimb2 = [xlima2[0]+xstep2, xlima2[1]-xstep2]
        ylimb1 = [ylima1[0]-ystep1, ylima1[1]+ystep1]
        ylimb2 = [ylima2[0]-ystep2, ylima2[1]+ystep2]
        ylimb3 = [ylima3[0]-ystep3, ylima3[1]+ystep3]

        self.ax.set_xlim(xlimb1[0], xlimb1[1])
        self.secaxx.set_xlim(xlimb2[0], xlimb2[1])
        self.ax.set_ylim(ylimb1[0], ylimb1[1])
        self.secaxy0.set_ylim(ylimb2[0], ylimb2[1])
        self.secaxy1.set_ylim(ylimb3[0], ylimb3[1])
        self.dataCanvas.draw()


    # method to zoom out
    def zoomOut(self, factor=1/4):
        # get original axis limits
        xlima1 = self.ax.get_xlim()
        xlima2 = self.secaxx.get_xlim()
        ylima1 = self.ax.get_ylim()
        ylima2 = self.secaxy0.get_ylim()
        ylima3 = self.secaxy1.get_ylim()

        xstep1 = abs(xlima1[1] - xlima1[0]) * factor
        xstep2 = abs(xlima2[1] - xlima2[0]) * factor
        ystep1 = abs(ylima1[1] - ylima1[0]) * factor
        ystep2 = abs(ylima2[1] - ylima2[0]) * factor
        ystep3 = abs(ylima3[1] - ylima3[0]) * factor

        # add steps
        xlimb1 = [xlima1[0]-xstep1, xlima1[1]+xstep1]
        xlimb2 = [xlima2[0]-xstep2, xlima2[1]+xstep2]
        ylimb1 = [ylima1[0]+ystep1, ylima1[1]-ystep1]
        ylimb2 = [ylima2[0]+ystep2, ylima2[1]-ystep2]
        ylimb3 = [ylima3[0]+ystep3, ylima3[1]-ystep3]
        # handle bounds
        if xlimb1[0] < 0:
            xlimb1[0] = 0
            xlimb2[0] = 0
        if xlimb1[1] > self.rdata.tnum:
            xlimb1[1] = self.rdata.tnum
            xlimb2[1] = self.rdata.navdf["dist"].iloc[-1]*1e-3
        if ylimb1[0] > self.rdata.snum:
            ylimb1[0] = self.rdata.snum
            ylimb2[0] = self.rdata.snum*self.rdata.dt
            ylimb3[0] = utils.twtt2depth(self.rdata.snum*self.rdata.dt, np.nanmean(self.rdata.asep), self.eps_r)
        if ylimb1[1] < 0:
            ylimb1[1] = 0
            ylimb2[1] = 0
            ylimb3[1] = 0
        self.ax.set_xlim(xlimb1[0], xlimb1[1])
        self.secaxx.set_xlim(xlimb2[0], xlimb2[1])
        self.ax.set_ylim(ylimb1[0], ylimb1[1])
        self.secaxy0.set_ylim(ylimb2[0], ylimb2[1])
        self.secaxy1.set_ylim(ylimb3[0], ylimb3[1])
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
                step3 = utils.twtt2depth(self.rdata.snum*self.rdata.dt, np.nanmean(self.rdata.asep), self.eps_r) - ylim3[0]
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


   # set_im is a method to set which rdata is being displayed
    def set_im(self, from_gui=False):
        if from_gui and self.rdata.flags.sim:
            self.im_status.set(int(not self.im_status.get()))

        if self.im_status.get() == 0:
            self.show_data()

        elif self.im_status.get() == 1:
            self.show_sim()


    # toggle to radar data
    def show_data(self):
        if not self.im_dat.get_visible():
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
            # redraw canvas
            # self.update_bg()
            self.fig.canvas.draw()


    # toggle to sim viewing
    def show_sim(self):
        if not self.im_sim.get_visible():
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
            # redraw canvas
            # self.update_bg()
            self.fig.canvas.draw()


    # get_pickState is a method to return the current picking state
    def get_pickState(self):
        return self.pick_state


    # return surface being picked (surface or subsurface)
    def get_pickSurf(self):
        return self.pick_surf


    # return horizon_paths
    def get_horizon_paths(self):
        return self.horizon_paths

    
    # receive horizon_paths
    def set_horizon_paths(self, horizon_paths):
        self.horizon_paths = copy.deepcopy(horizon_paths)
        for horizon, hdict in self.horizon_paths.items():
            x,y = utils.merge_paths(hdict)
            self.horizon_lns[horizon].set_data(x,y)


    # reverse horizon path objects
    def reverse(self):
        # horizon arrays have already been flipped within proc.reverse, but we need to reset the canvas by redrawing the horizons
        tmp = copy.deepcopy(self.rdata.pick.horizons)
        self.rm_horizon(rm_all=True, verify=False)
        for h in tmp.keys():
            self.rdata.pick.horizons[h] = tmp[h]
            self.set_picks(h)

        self.update_pickLabels()
        self.update_seg_opt_menu()
        self.update_bg()


    # return horizon colors
    def get_horizon_colors(self):
        return self.ln_colors["used"]

    
    # set tkinter menu font colors to match color name
    def set_menu_color(self, menu=None, var=None, *args):
        if menu is None:
            return
        if var=="color":
            c = self.ln_colors["hex"][self.ln_colors["str"].index(self.color.get())]
        elif var=="horVar":
            horizon = self.horVar.get()
            if not horizon:
                return
            c = self.ln_colors["used"][horizon]
        else:
            try:
                c = self.ln_colors["used"][var.get()]
            except:
                return
        menu.config(foreground=c, activeforeground=c, highlightcolor=c)


    # init_horizon is a method to initialize new horizon objects
    def init_horizon(self, horizon=None, skip_array=False):
        if self.get_pickState():
            return
        if not horizon:
            if self.popup.flag == 1:
                return            
            # create popup window to get new horizon name and interpreatation color
            hname = tk.StringVar()
            popup = self.popup.new(title="New Horizon")
            tk.Label(popup, text="Enter new horizon name:").pack(fill="both",expand=True)
            entry = tk.Entry(popup, textvar=hname, justify="center")
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
            for c, h in zip(self.ln_colors["str"], self.ln_colors["hex"]):
                dropdown["menu"].add_command(label=c, foreground=h, activeforeground=h, command=tk._setit(self.color, c))
            button = tk.Button(popup, text="OK", command=lambda:self.popup.close(flag=0), width=20).pack(side="left", fill="none", expand=True)
            button = tk.Button(popup, text="Cancel", command=lambda:[hname.set(""), self.popup.close(flag=-1)], width=20).pack(side="left", fill="none", expand=True)
            # wait for window to be closed
            self.parent.wait_window(popup)
            # remove the trace
            self.color.trace_vdelete("w", trace)
            horizon = hname.get()
            if (not horizon) or (self.popup.flag==-1):
                return

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
        self.horizon_lns[horizon], = self.ax.plot(x,y,lw=2,c=self.ln_colors["hex"][self.ln_colors["str"].index(self.color.get())])            
        # update horizon and segment options
        self.update_hor_opt_menu()  
        # set horVar to new horizon
        self.horVar.set(horizon)
        # update crosshairs and tmp pick line colors to match horizon color
        for ln in [self.tmp_horizon_ln, self.horizontal_line, self.vertical_line]:
            ln.set_color(self.ln_colors["str"][self.ln_colors["hex"].index(self.ln_colors["used"][horizon])])


    # rename horizon
    def rename_horizon(self, horizon=None):
        if self.get_pickState():
            return
        if horizon:
            if self.popup.flag == 1:
                return
            # create popup window to rename horizon
            hname = tk.StringVar()
            popup = self.popup.new(title="Rename Horizon")
            tk.Label(popup, text="Rename " + horizon + " horizon:").pack(fill="both",expand=True)
            entry = tk.Entry(popup, textvar=hname, justify="center")
            entry.pack(fill="both",expand=True) 
            entry.focus_set()
            # interpretation color selection dropdown - default to current horizon line color
            self.color.set(self.ln_colors["str"][self.ln_colors["hex"].index(self.ln_colors["used"][horizon])])
            tk.Label(popup, text="Interpretation color:").pack(fill="both", expand=True)
            dropdown = tk.OptionMenu(popup, self.color, *[None])
            dropdown["menu"].delete(0, "end")
            dropdown.config(width=20)
            dropdown.pack(fill="none", expand=True)
            self.set_menu_color(menu=dropdown, var="color")
            # trace change in self.color to self.set_menu_color
            trace = self.color.trace("w", lambda *args, menu=dropdown, var="color" : self.set_menu_color(menu, var))
            for c,h in zip(self.ln_colors["str"], self.ln_colors["hex"]):
                dropdown["menu"].add_command(label=c, foreground=h, activeforeground=h, command=tk._setit(self.color, c))
            button = tk.Button(popup, text="OK", command=lambda:self.popup.close(flag=0), width=20).pack(side="left", fill="none", expand=True)
            button = tk.Button(popup, text="Cancel", command=lambda:[hname.set(""), self.popup.close(flag=-1)], width=20).pack(side="left", fill="none", expand=True)
            # wait for window to be closed
            self.parent.wait_window(popup)
            # remove color trace
            self.color.trace_vdelete("w", trace)
            hname = hname.get()
            if self.popup.flag == -1:
                return
        
            # update line color
            c = self.ln_colors["hex"][self.ln_colors["str"].index(self.color.get())]
            self.ln_colors["used"][horizon] = c
            self.horizon_lns[horizon].set_color(c)
            self.horVar.set(horizon)

            # rename horizon path, line objects, and used line colors maintaining order
            if hname:
                self.horizon_paths = {hname if k==horizon else k:v for k,v in self.horizon_paths.items()}
                self.rdata.pick.horizons = {hname if k==horizon else k:v for k,v in self.rdata.pick.horizons.items()}
                self.horizon_lns = {hname if k==horizon else k:v for k,v in self.horizon_lns.items()}
                self.ln_colors["used"] = {hname if k==horizon else k:v for k,v in self.ln_colors["used"].items()}
                # set horVar to new horizon
                self.horVar.set(hname) 
                self.update_pickLabels()
            # update horizon and segment options
            self.update_hor_opt_menu()  
            self.update_bg()


    # remove horizon
    def rm_horizon(self, rm_all=False, horizon=None, verify=True):
        if len(self.horizons) < 1:
            return

        if rm_all:
            horizon = list(self.horizon_paths.keys())
            if verify:
                if tk.messagebox.askyesno("Warning","Remove all interpretation horizons?"):
                    verify = False
                else:
                    return

        if horizon is None:
            if self.popup.flag == 1:
                return
            # popup window to get horizon and segment option
            hname = tk.StringVar()
            hname.set(self.horVar.get())
            # create popup window to rename horizon
            popup = self.popup.new(title="Remove Horizon")
            # create horizon dropdown menu
            tk.Label(popup, text="Horizon:").pack(fill="both", expand=True)
            hdropdown = tk.OptionMenu(popup, hname, *[None])
            hdropdown.config(width=20)
            hdropdown.pack(fill="none", expand=True)
            # horizon dropdown with ln colors
            self.color.set(self.ln_colors["str"][self.ln_colors["hex"].index(self.ln_colors["used"][hname.get()])])
            self.set_menu_color(menu=hdropdown, var=hname)
            # trace change in self.color to self.set_menu_color
            trace0 = hname.trace("w", lambda *args, menu=hdropdown, var=hname : self.set_menu_color(menu, var))
            for key, val in self.ln_colors["used"].items():
                hdropdown["menu"].add_command(label=key, foreground=val, activeforeground=val, command=tk._setit(hname, key))
            hname.set(self.horVar.get())
            button = tk.Button(popup, text="OK", command=lambda:self.popup.close(flag=0), width=20).pack(side="left", fill="none", expand=True)
            button = tk.Button(popup, text="Cancel", command=lambda:[hname.set(""), self.popup.close(flag=-1)], width=20).pack(side="left", fill="none", expand=True)
            # wait for window to be closed
            self.parent.wait_window(popup)
            # remove color trace
            hname.trace_vdelete("w", trace0)
            horizon = hname.get()
            verify = False
            if (not horizon) or (self.popup.flag==-1):
                return

        if horizon:
            if verify and not tk.messagebox.askyesno("Warning","Remove " + horizon + " horizon?"):
                return
            if isinstance(horizon,str):
                horizon = [horizon]
            if self.get_pickState() and self.horVar.get() in horizon:
                self.set_pickState(False)
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
                if h == self.rdata.pick.srf:
                    self.rdata.pick.set_srf(None)
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
    def edit_segment(self, horizon=None, seg=None, verify=True):
        if len(self.horizons) < 1 or self.get_pickState():
            return
        # popup window to get horizon and segment option
        if horizon is None and seg is None:
            if self.popup.flag == 1:
                return
            hname = tk.StringVar()
            hname.set(self.horVar.get())
            s = tk.IntVar()
            s.set(self.segVar.get())
            # create popup window to rename horizon
            popup = self.popup.new(title="Edit Horizon Segment")
            # create horizon dropdown menu
            tk.Label(popup, text="Horizon:").pack(fill="both", expand=True)
            hdropdown = tk.OptionMenu(popup, hname, *[None])
            hdropdown.config(width=20)
            hdropdown.pack(fill="none", expand=True)
            # horizon dropdown with ln colors
            self.color.set(self.ln_colors["str"][self.ln_colors["hex"].index(self.ln_colors["used"][hname.get()])])
            self.set_menu_color(menu=hdropdown, var=hname)
            # trace change in self.color to self.set_menu_color
            trace0 = hname.trace("w", lambda *args, menu=hdropdown, var=hname : self.set_menu_color(menu, var))
            for key, val in self.ln_colors["used"].items():
                hdropdown["menu"].add_command(label=key, foreground=val, activeforeground=val, command=tk._setit(hname, key))

            # create seg dropdown menu
            tk.Label(popup, text="Segment:").pack(fill="both", expand=True)
            sdropdown = tk.OptionMenu(popup, s, *[None])
            sdropdown.config(width=20)
            sdropdown.pack(fill="none", expand=True)
            # trace change in self.color to self.set_menu_color
            trace1 = hname.trace("w", lambda *args, last=True, menu=sdropdown, hvar=hname, svar=s: self.update_seg_opt_menu(last, menu, hvar, svar))
            hname.set(self.horVar.get())
            button = tk.Button(popup, text="OK", command=lambda:self.popup.close(flag=0), width=20).pack(side="left", fill="none", expand=True)
            button = tk.Button(popup, text="Cancel", command=lambda:[hname.set(""), self.popup.close(flag=-1)], width=20).pack(side="left", fill="none", expand=True)
            # wait for window to be closed
            self.parent.wait_window(popup)
            # remove color trace
            hname.trace_vdelete("w", trace0)
            hname.trace_vdelete("w", trace1)
            horizon = hname.get()
            seg = s.get()
            verify = False
            if (not horizon) or (seg is None) or (self.popup.flag==-1):
                return

        # ensure segment belongs to horizon and that interpretations have been made
        if (seg in self.horizon_paths[horizon]):
            if np.isnan(self.horizon_paths[horizon][seg].x).all():
                return
            if verify and not (tk.messagebox.askokcancel("Warning", "Edit interpretation segment " + horizon + "_" + str(seg) + "?", icon="warning")):
                return
            self.edit_flag = True
            self.set_pickState(True)
            # find indices of picked traces
            picks_idx = np.where(~np.isnan(self.horizon_paths[horizon][seg].x))[0]
            # update self.edit_path
            self.edit_path = path(picks_idx, self.horizon_paths[horizon][seg].y[picks_idx])
            # return picked traces to xln list
            self.tmp_horizon_path.x = picks_idx[::20].tolist()
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
        if len(self.horizons) < 1:
            return
        # popup window to get horizon and segment option
        if horizon is None and seg is None:
            if self.popup.flag == 1:
                return
            hname = tk.StringVar()
            hname.set(self.horVar.get())
            s = tk.IntVar()
            s.set(self.segVar.get())
            # create popup window to rename horizon
            popup = self.popup.new(title="Remove Horizon Segment")
            # create horizon dropdown menu
            tk.Label(popup, text="Horizon:").pack(fill="both", expand=True)
            hdropdown = tk.OptionMenu(popup, hname, *[None])
            hdropdown.config(width=20)
            hdropdown.pack(fill="none", expand=True)

            # horizon dropdown with ln colors
            self.color.set(self.ln_colors["str"][self.ln_colors["hex"].index(self.ln_colors["used"][hname.get()])])
            self.set_menu_color(menu=hdropdown, var=hname)
            # trace change in self.color to self.set_menu_color
            trace0 = hname.trace("w", lambda *args, menu=hdropdown, var=hname : self.set_menu_color(menu, var))
            for key, val in self.ln_colors["used"].items():
                hdropdown["menu"].add_command(label=key, foreground=val, activeforeground=val, command=tk._setit(hname, key))
            # create seg dropdown menu
            tk.Label(popup, text="Segment:").pack(fill="both", expand=True)
            sdropdown = tk.OptionMenu(popup, s, *[None])
            sdropdown.config(width=20)
            sdropdown.pack(fill="none", expand=True)
            # trace change in self.color to self.set_menu_color
            trace1 = hname.trace("w", lambda *args, last=True, menu=sdropdown, hvar=hname, svar=s: self.update_seg_opt_menu(last, menu, hvar, svar))
            hname.set(self.horVar.get())
            button = tk.Button(popup, text="OK", command=lambda:self.popup.close(flag=0), width=20).pack(side="left", fill="none", expand=True)
            button = tk.Button(popup, text="Cancel", command=lambda:[hname.set(""), self.popup.close(flag=-1)], width=20).pack(side="left", fill="none", expand=True)
            # wait for window to be closed
            self.parent.wait_window(popup)
            # remove hname traces
            hname.trace_vdelete("w", trace0)
            hname.trace_vdelete("w", trace1)
            horizon = hname.get()
            seg = s.get()
            if (not horizon) or (seg is None) or (self.popup.flag==-1):
                return
        

        # ensure segment belongs to horizon and that interpretations have been made
        if (seg in self.horizon_paths[horizon]):
            if (np.isnan(self.horizon_paths[horizon][seg].x).all()) and not (self.edit_flag):
                return

            if not (tk.messagebox.askokcancel("Warning", "Remove interpretation segment " + horizon + "_" + str(seg) + "?", icon="warning")):
                return
            # if currently editing layer, clear tmp horizon objects
            if self.edit_flag:
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
            self.update_seg_opt_menu(last=True)
            # reset line object for horizon
            x,y = utils.merge_paths(self.horizon_paths[horizon])
            self.horizon_lns[horizon].set_data(x,y)
            self.update_bg()
    

    # set_pickState is a method to handle the pick state for a given surface as well as pick labels
    def set_pickState(self, state=False):
        horizon = self.horVar.get()
        seg=self.segVar.get()
        # temporary path object length
        l = len(self.tmp_horizon_path.x)                
        # handle pick state set to true
        if state:
            if not horizon:
                self.init_horizon()
                return
            # if pick state was previously true
            if self.get_pickState():
                if l >= 2:
                    self.pick_interp(horizon=horizon,seg=seg)
                    self.plot_picks(horizon=horizon)
                    # if subsequent segment doesn't already exist, initialize
                    if (seg + 1) not in self.horizon_paths[horizon]:
                        self.init_segment(horizon)
                    else:
                        self.segVar.set(seg + 1)
                else:
                    self.clear_last()
            # if pick state was previously false
            else:
                self.startbutton.config(relief="sunken")
                self.stopbutton.config(relief="raised")
                # temporarily disable horizon and segment menus
                self.horMenu.config(state="disabled")
                self.segMenu.config(state="disabled")

        # handle pick state set to false
        else:
            self.startbutton.config(relief="raised")
            self.stopbutton.config(relief="sunken")
            # reactivate horizon and segment menus
            self.horMenu.config(state="active")
            self.segMenu.config(state="active")
            # if pick state was previously true
            if self.get_pickState():
                if l >=  2:
                    # handle previously editing
                    if self.edit_flag:
                        # if no edits made, return to previous segment picks
                        x = self.edit_path.x[::20].tolist()
                        y = self.edit_path.y[::20].tolist()
                        if (x == self.tmp_horizon_path.x) and (y == self.tmp_horizon_path.y):
                            self.tmp_horizon_path.x = self.edit_path.x.tolist()
                            self.tmp_horizon_path.y = self.edit_path.y.tolist()
                    # interpolate and plot picks
                    self.pick_interp(horizon=horizon,seg=seg)
                    self.plot_picks(horizon=horizon)
                    if (seg + 1) not in self.horizon_paths[horizon]:
                        self.init_segment(horizon)
                    else:
                        self.segVar.set(seg + 1)
                # if less than 2 picks, clear
                else:
                    self.clear_last()
                    del self.horizon_paths[horizon][list(self.horizon_paths[horizon].keys())[-1]]
            # reset edit_flag
            self.edit_flag = state
        # update pick_state to current state
        self.pick_state = state
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
                    sample[_i] = int(sample[_i] - (winSize/2)) + np.argmax(np.abs(self.rdata.dat)[int(sample[_i] - (winSize/2)):int(sample[_i] + (winSize/2)), picked_traces[_i]])
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


    # clear last pick
    def clear_last(self):
        if self.pick_state == True:
            if  len(self.tmp_horizon_path.x) >= 1: 
                del self.tmp_horizon_path.x[-1:]
                del self.tmp_horizon_path.y[-1:]
                # reset self.tmp_horizon_ln, then blit
                self.tmp_horizon_ln.set_data(self.tmp_horizon_path.x, self.tmp_horizon_path.y)
                self.blit()


    # set_picks is a method to set imported pick arrays to horizon_paths
    def set_picks(self, horizon=None):
        if horizon:
            # set horizon color to first unused color
            color = [c for c in self.ln_colors["hex"] if c not in list(self.ln_colors["used"].values())][0]
            self.color.set(self.ln_colors["str"][self.ln_colors["hex"].index(color)])
            self.init_horizon(horizon=horizon,skip_array=True)
            # split horizon array into segments
            idx = utils.nonan_idx_array(self.rdata.pick.horizons[horizon])
            clumps = utils.clump_array(idx)
            for _i, clump in enumerate(clumps):
                clump_arr = np.asarray(clump).astype(int)
                self.horizon_paths[horizon][_i].x[clump_arr] = clump_arr
                self.horizon_paths[horizon][_i].y[clump_arr] = self.rdata.pick.horizons[horizon][clump_arr]
                self.init_segment(horizon=horizon)
            x,y = utils.merge_paths(self.horizon_paths[horizon])
            self.horizon_lns[horizon].set_data(x,y)


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
    def update_seg_opt_menu(self, last=False, menu=None, hvar=None, svar=None, *args):
        if menu is None:
            menu = self.segMenu
        if hvar is None:
            hvar = self.horVar
        if svar is None:
            svar = self.segVar
        horizon = hvar.get()
        menu["menu"].delete(0, "end")
        if horizon:
            for seg in sorted(self.horizon_paths[horizon].keys()):
                menu["menu"].add_command(label=seg, command=tk._setit(svar, seg))
            # set segment selection to last
            if last:
                svar.set(seg)


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
        if self.rdata:
            x, y = event.xdata, event.ydata
            self.horizontal_line.set_ydata(y)
            self.vertical_line.set_xdata(x)
            self.ax.figure.canvas.restore_region(self.axbg)
            self.ax.draw_artist(self.horizontal_line)
            self.ax.draw_artist(self.vertical_line)
            self.blit()


    # update_figsettings
    def update_figsettings(self, figsettings=None):
        if figsettings:
            self.figsettings = figsettings
        # update all label sizes
        fs = self.figsettings["fontsize"].get()
        plt.rcParams.update({'font.size': fs})
        for item in ([self.ax.xaxis.label, self.ax.yaxis.label, self.secaxx.xaxis.label, self.secaxy0.yaxis.label, self.secaxy1.yaxis.label] +
                    self.ax.get_xticklabels() + self.ax.get_yticklabels() + self.secaxx.get_xticklabels() + self.secaxy0.get_yticklabels() + self.secaxy1.get_yticklabels() + self.ann_list):
            item.set_fontsize(fs)
        self.ax.title.set_size(fs)
        self.s_cmin.label.set_fontsize(fs)
        self.s_cmax.label.set_fontsize(fs)
        self.s_cmin.valtext.set_fontsize(fs)
        self.s_cmax.valtext.set_fontsize(fs)
        self.cmap_reset_button.label.set_fontsize(fs)
        # update title visibility
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
        self.verticalClip(self.figsettings["figclip"][0].get(), self.figsettings["figclip"][1].get())
        w0 ,h0 = self.fig.get_size_inches()    # get pre-save figure size
        w, h = self.figsettings["figsize"].get().split(",")
        self.fig.set_size_inches((float(w),float(h)))    # set figsize to wide aspect ratio
        # temporarily turn sliders to invisible for saving image
        self.ax_cmax.set_visible(False)
        self.ax_cmin.set_visible(False)
        self.reset_ax.set_visible(False)
        self.secaxy1.set_visible(False)
        # hide pick annotations
        vis = self.ann_vis
        if vis:
            self.show_labels(vis=False)  

        # save data fig with and without picks
        if self.im_status.get() ==1:
            self.show_data()
        self.show_picks(vis=False)
        export.fig(f_saveName.rstrip(f_saveName.split("/")[-1]) + self.rdata.fn + ".png", self.fig)
        self.show_picks(vis=True)
        export.fig(f_saveName, self.fig)
    
        # save sim fig if sim exists
        if self.rdata.flags.sim:
            self.show_sim()
            # ensure picks are hidden
            # self.pick_vis.set(False)
            self.show_picks(vis=False)
            export.fig(f_saveName.rstrip(f_saveName.split("/")[-1]) + self.rdata.fn + "_sim.png", self.fig)
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


class path():
    # initialize a path object to hold x,y paths for plotting - list or array like
    def __init__(self, x=None, y=None):
        self.x = x      # x array/list
        self.y = y      # y array/list