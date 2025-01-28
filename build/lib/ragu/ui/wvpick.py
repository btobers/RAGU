# RAGU - Radar Analysis Graphical Utility
#
# copyright © 2020 btobers <tobers.brandon@gmail.com>
#
# distributed under terms of the GNU GPL3.0 license
"""
wvpick class is a tkinter frame which handles the RAGU waveform view and radar pick optimization
"""
### imports ###
from ragu.tools import utils
import numpy as np
from scipy.interpolate import CubicSpline
from scipy.signal import find_peaks
import tkinter as tk
import sys,os,time,copy
import matplotlib as mpl
mpl.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
# try:
#     plt.rcParams["font.family"] = "Times New Roman"
# except:
#     pass

class wvpick(tk.Frame):
    # wvpick is a class to optimize the picking of horizons from radar data
    def __init__(self, parent, button_tip, reset_picks, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)
        self.parent = parent
        self.button_tip = button_tip
        self.reset_picks = reset_picks
        self.winSize = tk.IntVar(value=100)
        self.stepSize = tk.IntVar(value=10)
        self.horVar = tk.StringVar()
        self.segVar = tk.IntVar()
        self.color = tk.StringVar()
        self.interp_type = tk.StringVar()
        self.interp_type.set("cubic")
        self.setup()

    def setup(self):
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

        # infoFrame exists for options to be added based on optimization needs
        tk.Label(infoFrame, text = "Amplitude Window [#Samples]: ").pack(side="left")
        entry = tk.Entry(infoFrame, textvariable=self.winSize, width = 5)
        entry.pack(side="left")
        self.button_tip(self.parent, entry, \
            "Pick amplitude window size. Window size (number of samples) centered on \
            manual picks from which to select maximum amplitude using auto-pick optimization.")
        tk.ttk.Separator(infoFrame,orient="vertical").pack(side="left", fill="both", padx=10, pady=4)

        tk.Label(infoFrame, text = "Step Size [#Traces]: ").pack(side="left")
        entry = tk.Entry(infoFrame, textvariable=self.stepSize, width = 5)
        entry.pack(side="left")
        self.button_tip(self.parent, entry, \
            "Number of traces to move forward and backwards in radargram upon ←/→ button or key press.")
        tk.ttk.Separator(infoFrame,orient="vertical").pack(side="left", fill="both", padx=10, pady=4)

        button = tk.Button(infoFrame, text="←", command = self.stepBackward, pady=0)
        button.pack(side="left")
        self.button_tip(self.parent, button, "Step backwards")
        button = tk.Button(infoFrame, text="→", command = self.stepForward, pady=0)
        button.pack(side="left")
        self.button_tip(self.parent, button, "Step forwards")
        tk.ttk.Separator(infoFrame,orient="vertical").pack(side="left", fill="both", padx=10, pady=4)

        # set up frame to hold pick information
        interpFrameT = tk.Frame(interpFrame)
        interpFrameT.pack(fill="both",expand=True)
        interpFrameT.pack_propagate(0)
        interpFrameB = tk.Frame(interpFrame)
        interpFrameB.pack(fill="both",expand=True)
        interpFrameB.pack_propagate(0)
        
        interpFrameTl = tk.Frame(interpFrameT,width=250,relief="ridge", borderwidth=1)
        interpFrameTl.pack(side="left",fill="both",expand=True)
        interpFrameTl.pack_propagate(0)
        interpFrameTr = tk.Frame(interpFrameT,width=200)
        interpFrameTr.pack(side="left",fill="both",expand=True)
        interpFrameTr.pack_propagate(0)

        interpFrameBl = tk.Frame(interpFrameB,width=250,relief="ridge", borderwidth=1)
        interpFrameBl.pack(side="left",fill="both",expand=True)
        interpFrameBl.pack_propagate(0)
        interpFrameBr = tk.Frame(interpFrameB,width=200)
        interpFrameBr.pack(side="left",fill="both",expand=True)
        interpFrameBr.pack_propagate(0)

        tk.Label(interpFrameTl,text="{0:<8}".format("Horizon:")).pack(side="left")
        button = tk.Button(interpFrameTl, text="Reset", width=6, command=self.reset)
        button.pack(side="right")
        self.button_tip(self.parent, button, "Reset pick data from profile interpretations")
        self.horMenu = tk.OptionMenu(interpFrameTl, self.horVar, *[None])
        self.horMenu.pack(side="right")
        self.horMenu.config(width=10)
        self.horVar.trace("w", self.update_seg_opt_menu) 
        self.horVar.trace("w", self.seg_select)
        self.horVar.trace("w", lambda *args, menu=self.horMenu : self.set_menu_color(menu))

        tk.Label(interpFrameBl,text="{0:<8}".format("Segment:")).pack(side="left")
        button = tk.Button(interpFrameBl, text=None, width=6, command=None)
        button.config(relief="sunken", state="disabled")
        button.pack(side="right")
        self.segMenu = tk.OptionMenu(interpFrameBl, self.segVar, *[None])
        self.segMenu.pack(side="right")
        self.segMenu.config(width=10)
        self.segVar.trace("w", self.first_trace)

        button = tk.Radiobutton(interpFrameTr, text="Linear", variable=self.interp_type, value="linear")
        button.pack(side="left",fill="both",expand=True)
        self.button_tip(self.parent, button, "Linear interpolation between manual pick modifications")

        button = tk.Radiobutton(interpFrameTr,text="Cubic Spline", variable=self.interp_type, value="cubic")
        button.pack(side="left",fill="both",expand=True)
        self.button_tip(self.parent, button, "Cubic spline interpolation between manual pick modifications")

        button = tk.Button(interpFrameBr, text="Auto-Optimize", command=self.auto_repick)
        button.pack(side="left",fill="both",expand=True)
        self.button_tip(self.parent, button, "Automatically optimize profile view interpretation picks for current horizon segment\
                                            by selecting maximum aplitude sample for each radargram trace within a window of the\
                                            specified size centered on existing profile picks.")

        button = tk.Button(interpFrameBr, text="Interpolate", command=self.interp_repick)
        button.pack(side="left",fill="both",expand=True)
        self.button_tip(self.parent, button, "Interpolate between manually updated waveform picks using the spefied interpolation method\
                                            for  current horizon segment.")

        # create figure object and datacanvas from it
        plt.rcParams.update({'font.size': 12})
        self.fig = mpl.figure.Figure()
        self.fig.patch.set_facecolor("#d9d9d9")
        self.dataCanvas = FigureCanvasTkAgg(self.fig, self.parent)
        self.dataCanvas.get_tk_widget().pack(in_=self.dataFrame, side="bottom", fill="both", expand=1) 
        self.click = self.fig.canvas.mpl_connect("button_press_event", self.onpress)
        self.unclick = self.fig.canvas.mpl_connect('button_release_event', self.onrelease)
        self.draw_cid = self.fig.canvas.mpl_connect("draw_event", self.update_bg)
        self.mousemotion = self.fig.canvas.mpl_connect('motion_notify_event', self.on_mouse_move)

        # add toolbar to plot
        self.toolbar = NavigationToolbar2Tk(self.dataCanvas, toolbarFrame)
        self.toolbar.pack(side="left")
        # self.toolbar.update()

        # create the figure axes
        self.ax = self.fig.add_subplot(111)
        self.fig.tight_layout(rect=[.02,.05,.97,1])
        self.ax.set_visible(False)

        # update the canvas
        self.dataCanvas._tkcanvas.pack()
        self.dataCanvas.draw()
    

    # set up variables
    def set_vars(self):
        self.rdata = None
        self.horizon_paths_opt = None
        self.ln_colors = {}
        self.horizons = []
        self.repick_idx = {}        # dictionary of indeces of repicked traces for each seg
        self.t  = None              # hold current trace number


    # set_data is a method to receive the radar data
    def set_data(self, rdata):
        # get data in dB
        self.rdata = rdata


    # receive horizon paths from impick
    def set_horizon_paths(self, horizon_paths):
        self.horizon_paths = copy.deepcopy(horizon_paths)
        self.horizon_paths_opt = copy.deepcopy(horizon_paths)
        self.horizons = list(self.horizon_paths_opt)
        self.nhorizons = len(self.horizons)
        self.update_hor_opt_menu()
        self.update_seg_opt_menu()

    
    # return optimized horizon paths
    def get_horizon_paths(self):
        return self.horizon_paths_opt


    # receive horizon line colors
    def set_horizon_colors(self, ln_colors):
        self.ln_colors = ln_colors


    # reset returns updated picks from gui
    def reset(self):
        if tk.messagebox.askyesno("Reset","Reset optimized horizon interpretations?"):
            self.reset_picks(force=True)


    # set_picks is a method which receives horizon interpretations for optimization
    def set_picks(self):
        self.ax.set_visible(True)
        # create lists of first and last picked trace number for each seg in each horizon
        self.segment_traces = {}
        # create dict to hold current trace number for each horizon
        self.trace = {}
        if self.nhorizons > 0:
            # iterate through horizon_paths
            for horizon, hdict in self.horizon_paths_opt.items():
                self.segment_traces[horizon] = bounds([],[])
                self.repick_idx[horizon] = []
                self.trace[horizon] = None
                # iterate through segments for each horizon
                for seg, path in hdict.items():
                    picked_traces = np.where(~np.isnan(path.x))[0]
                    if picked_traces.shape[0] > 0:
                        self.segment_traces[horizon].first.append(picked_traces[0])
                        self.segment_traces[horizon].last.append(picked_traces[-1])
                        if seg == 0:
                            self.trace[horizon] = picked_traces[0]
            # set horVar
            self.horVar.set(self.horizons[-1])
        else:
            self.trace[''] = 0


    # plot_wv is a method to draw the waveform on the datacanvas
    def plot_wv(self, *args):
        horizon = self.horVar.get()
        seg = self.segVar.get()
        winSize = self.winSize.get()
        # get previous x_lim
        xlim = self.ax.get_xlim()
        self.ax.clear()

        # plot trace power
        self.t = self.trace[horizon]
        self.ax.plot(self.rdata.proc.curr_dB[:,self.t], c="0.5")
        self.ax.set(xlabel = "Sample", ylabel = "Power [dB]", title="Trace: " + str(int(self.trace[horizon] + 1)) + "/" + str(int(self.rdata.tnum)))

        # get pick value range
        val = np.array(())

        # if self.nhorizons > 0:
        for horizon in self.horizons:
            # get sample index of pick for given trace
            for seg in self.horizon_paths_opt[horizon].keys():
                pick_idx0 = self.horizon_paths[horizon][seg].y[self.t]
                pick_idx1 = self.horizon_paths_opt[horizon][seg].y[self.t]
                val = np.append(val, (pick_idx0+pick_idx1)//2)
                if not np.isnan(pick_idx0):
                    self.ax.axvline(x = pick_idx0, c=self.ln_colors[horizon], label=horizon + "_" + str(seg))
                    if not np.isnan(pick_idx1) and (pick_idx0 != pick_idx1):
                        self.ax.axvline(x = pick_idx1, c=self.ln_colors[horizon], ls = "--", label=horizon + "_" + str(seg) + "_v2")
        
        self.ax.set(xlim=(0,self.rdata.snum))
        # save un-zoomed view to toolbar
        self.toolbar.push_current()

        # zoom in to window around horizons
        if not np.isnan(val).all():
            if xlim == (0,1) or xlim == (0,self.rdata.snum):
                min_ = np.nanmin(val) - (2*winSize)
                max_ = np.nanmax(val) + (2*winSize)
                self.ax.set(xlim=(min_,max_))
            else:
                self.ax.set(xlim=xlim)

        if len(self.ax.lines) > 1:
            self.ax.legend(loc="lower right")

        # initialize cursor crosshair lines
        self.horizontal_line = self.ax.axhline(color="r", lw=1, ls=":")
        self.vertical_line = self.ax.axvline(color="r", lw=1, ls=":")

        self.dataCanvas.draw()


    # full extent for trace
    def fullExtent(self):
        horizon = self.horVar.get()
        self.ax.set_xlim(0, self.rdata.snum)
        self.ax.set_ylim(self.rdata.proc.curr_dB[:,self.trace[horizon]].min(), self.rdata.proc.curr_dB[:,self.trace[horizon]].max())
        self.dataCanvas.draw()


    # stepBackward is a method to move backwards by the number of traces entered to stepSize
    def stepBackward(self):
        horizon = self.horVar.get()
        seg = self.segVar.get()
        step = self.stepSize.get()
        newTrace = self.trace[horizon] - step
        if self.nhorizons > 0:
            firstTrace_seg = self.segment_traces[horizon].first[seg]
            if newTrace >= firstTrace_seg:
                self.trace[horizon] -= step
            elif newTrace < firstTrace_seg:
                if self.trace[horizon] == firstTrace_seg:
                    return
                else:
                    self.trace[horizon] = firstTrace_seg

        else:
            if newTrace >= 0:
                self.trace[''] -= step
            elif newTrace < 0:
                if self.trace[''] == 0:
                    return
                else:
                    self.trace[''] = 0
            
        self.plot_wv()


    # stepForward is a method to move forward by the number of traces entered to stepSize
    def stepForward(self):
        horizon = self.horVar.get()
        seg = self.segVar.get()
        step = self.stepSize.get()
        newTrace = self.trace[horizon] + step
        if self.nhorizons > 0:
            lastTrace_seg = self.segment_traces[horizon].last[seg]
            if newTrace <= lastTrace_seg:
                self.trace[horizon] += step
            # if there are less traces left in the pick seg than the step size, move to the last trace in the seg
            elif newTrace > lastTrace_seg:
                if self.trace[horizon] == lastTrace_seg:
                    return
                    # if seg + 2 <= self.nhorizons and tk.messagebox.askokcancel("Next Sement","Finished optimization of current pick seg\n\tProceed to next seg?") == True:
                        # self.segVar.set(seg + 1) 
                else:
                    self.trace[horizon] = self.segment_traces[horizon].last[seg]
        
        else:
            if newTrace <= self.rdata.tnum:
                self.trace[''] += step
            elif newTrace > self.rdata.tnum:
                if self.trace[''] == self.rdata.tnum - 1:
                    return
                else:
                    self.trace[''] = self.rdata.tnum - 1

        self.plot_wv()


    # seg_select 
    def seg_select(self, *args):
        if self.t is None:
            return
        horizon = self.horVar.get()
        seg = self.segVar.get()
        self.trace[horizon] = self.t
        t0_list = self.segment_traces[horizon].first
        t1_list = self.segment_traces[horizon].last
        # if switched horizon, select segment which has current trace, if any
        for _i in range(len(t0_list)):  
            if (t0_list[_i] < self.t) and (t1_list[_i] > self.t):
                self.segVar.set(_i)
                self.t = None
                break
            else: 
                continue


    # first_trace updates the segment selection sets self.trace[horizon] to the first trace for the selected segment and replots
    def first_trace(self, *args):
        if self.t is not None:
            horizon = self.horVar.get()
            seg = self.segVar.get()
            t0_list = self.segment_traces[horizon].first
            if seg > len(t0_list):
                return
            self.trace[horizon] = t0_list[seg]
        # reset xlim
        self.ax.set(xlim=(0,self.rdata.snum))
        self.plot_wv()    


    # auto_repick is a method to automatically optimize subsurface picks by selecting the maximul amplitude sample within the specified window around existing picks
    def auto_repick(self):
        if self.nhorizons > 0:
            horizon = self.horVar.get()
            seg = self.segVar.get()
            winSize = self.winSize.get()
            x = np.arange(self.segment_traces[horizon].first[seg], self.segment_traces[horizon].last[seg] + 1)
            y = self.horizon_paths[horizon][seg].y[x]
            for _i in range(len(x)):
                if not np.isnan(y[_i]):
                    # find argmax for window for given data trace in pick
                    max_idx = np.nanargmax(self.rdata.proc.curr_dB[int(y[_i] - (winSize/2)):int(y[_i] + (winSize/2)), x[_i]])
                    # add argmax index to pick_dict1 - account for window index shift
                    self.horizon_paths_opt[horizon][seg].y[x[_i]] = max_idx + int(y[_i] - (winSize/2))
            self.plot_wv()


    # manual_repick is a method to manually adjust existing picks by clicking along the displayed waveform
    def manual_repick(self, event):
        if (not self.nhorizons > 0) or (event.inaxes != self.ax):
            return
        horizon = self.horVar.get()
        seg = self.segVar.get()
        # append trace number to repick_idx list to keep track of indeces for interpolation
        if (len(self.repick_idx[horizon]) == 0) or (self.repick_idx[horizon][-1] != self.trace[horizon]):
            self.repick_idx[horizon].append(self.trace[horizon])
        
        self.horizon_paths_opt[horizon][seg].y[self.trace[horizon]] = int(event.xdata)        
        self.plot_wv()


    # interp_repick is a method to interpolate between manually refined subsurface picks
    def interp_repick(self):
        horizon = self.horVar.get()
        seg = self.segVar.get()
        interp = self.interp_type.get()
        if len(self.repick_idx[horizon]) < 2:
            return
        # get indeces of repicked traces
        xp = self.repick_idx[horizon]
        # generate array of indices between first and last optimized pick
        interp_idx = np.arange(xp[0],xp[-1] + 1)

        if interp == "linear":
            # get twtt values at repicked indicesself.pick_dict1
            fp = self.horizon_paths_opt[horizon][seg].y[xp]
            # interpolate repicked values for seg
            self.horizon_paths_opt[horizon][seg].y[interp_idx] = np.interp(interp_idx, xp, fp)            

        elif interp == "cubic":
            # cubic spline between picks
            cs = CubicSpline(xp, self.horizon_paths_opt[horizon][seg].y[xp])
            # add cubic spline output interpolation to pick dictionary
            self.horizon_paths_opt[horizon][seg].y[interp_idx] = cs([interp_idx]).astype(int)


    # set tkinter menu font colors to match color name
    def set_menu_color(self, menu=None, *args):
        horizon = self.horVar.get()
        if not horizon:
            return
        c = self.ln_colors[horizon]
        menu.config(foreground=c, activeforeground=c, highlightcolor=c)


    # update the horizon menu
    def update_hor_opt_menu(self):
        self.horizons = list(self.horizon_paths_opt.keys())
        self.horMenu["menu"].delete(0, "end")
        for i, horizon in enumerate(self.horizons):
            c = self.ln_colors[horizon]
            self.horMenu["menu"].add_command(label=horizon, foreground=c, activeforeground=c, command=tk._setit(self.horVar, horizon))


    # update the horizon seg menu based on how many segments exist for given seg
    def update_seg_opt_menu(self, *args):
        horizon = self.horVar.get()
        self.segMenu["menu"].delete(0, "end")
        if horizon:
            for seg in sorted(self.horizon_paths_opt[horizon].keys()):
                self.segMenu["menu"].add_command(label=seg, command=tk._setit(self.segVar, seg))


    # show_artists
    def show_artists(self, val=True):
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
        self.show_artists(True)
        self.blit()


    # update the figure, without needing to redraw the "axbg" artists
    def blit(self):
        self.fig.canvas.restore_region(self.axbg)
        for _i in self.ax.lines:
            self.ax.draw_artist(_i)
        self.fig.canvas.blit(self.ax.bbox)


    # onpress gets the time of the button_press_event
    def onpress(self,event):
        self.time_onclick = time.time()


    # onrelease calls manual_repick if the time between the button press and release events
    # is below a threshold so that segments aren't drawn while trying to zoom or pan
    def onrelease(self,event):
        if event.inaxes == self.ax:
            if event.button == 1 and ((time.time() - self.time_onclick) < 0.25):
                self.manual_repick(event)


    # on_mouse_move blit crosshairs
    def on_mouse_move(self, event):
        if self.rdata is None:
            return
        x = event.xdata
        y = event.ydata
        if event.inaxes == self.ax:
            y = self.rdata.proc.curr_dB[int(x),self.trace[self.horVar.get()]]
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

        for item in ([self.ax.title, self.ax.xaxis.label, self.ax.yaxis.label] +
                    self.ax.get_xticklabels() + self.ax.get_yticklabels()):
            item.set_fontsize(self.figsettings["fontsize"].get())

        self.ax.title.set_visible(self.figsettings["figtitle"].get())

        self.fig.canvas.draw()


    # clear is a method to clear the wavePick tab and stored data when a new track is loaded
    def clear(self):
        self.ax.clear()
        self.dataCanvas.draw()
        self.set_vars()


class bounds():
    # initialize a bounds object to hold first,last trace for interpretation segments - list or array like
    def __init__(self, first=None, last=None):
        self.first = first      # x array/list
        self.last = last      # y array/list