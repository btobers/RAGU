"""
impick class is a tkinter frame which handles the NOSEpick profile view and radar data picking
"""
### imports ###
from tools import utils
from ui import basemap
import numpy as np
import tkinter as tk
import sys,os,time,fnmatch
import matplotlib as mpl
mpl.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.widgets import Cursor
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from scipy.interpolate import CubicSpline

class impick(tk.Frame):
    # impick is a class to pick horizons from a radar image
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

        self.im_status = tk.StringVar()
        # add radio buttons for toggling between radargram and clutter-sim
        radarRadio = tk.Radiobutton(infoFrame, text="radargram", variable=self.im_status, value="data",command=self.show_data)
        radarRadio.pack(side="left")
        clutterRadio = tk.Radiobutton(infoFrame,text="cluttergram", variable=self.im_status, value="clut",command=self.show_clut)
        clutterRadio.pack(side="left")
        tk.ttk.Separator(infoFrame,orient="vertical").pack(side="left", fill="both", padx=10, pady=4)

        # add radio buttons for toggling pick visibility
        self.pick_vis = tk.BooleanVar()
        tk.Label(infoFrame, text="pick visibility: ").pack(side="left")
        tk.Radiobutton(infoFrame,text="on", variable=self.pick_vis, value=True, command=self.show_picks).pack(side="left")
        tk.Radiobutton(infoFrame,text="off", variable=self.pick_vis, value=False, command=self.hide_picks).pack(side="left")
        tk.ttk.Separator(infoFrame,orient="vertical").pack(side="left", fill="both", padx=10, pady=4)

        # add radio buttons for toggling pick labels
        self.pick_ann_vis = tk.BooleanVar()
        tk.Label(infoFrame, text="pick segment labels: ").pack(side="left")
        tk.Radiobutton(infoFrame,text="on", variable=self.pick_ann_vis, value=True, command=self.show_pickLabels).pack(side="left")
        tk.Radiobutton(infoFrame,text="off", variable=self.pick_ann_vis, value=False, command=self.show_pickLabels).pack(side="left")
        tk.ttk.Separator(infoFrame,orient="vertical").pack(side="left", fill="both", padx=10, pady=4)

        tk.Button(infoFrame, text="edit", command=self.edit_pkLayer).pack(side="right")
        tk.Button(infoFrame, text="delete", command=self.delete_pkLayer).pack(side="right")

        self.layerVar = tk.IntVar()
        self.layers=[None]
        self.layerMenu = tk.OptionMenu(infoFrame, self.layerVar, *self.layers)
        self.layerMenu.pack(side="right",pady=0)
        tk.Label(infoFrame,text="subsurface pick segment: ").pack(side="right")

        self.pickLabel = tk.Label(toolbarFrame, font= "Verdana 10")
        self.pickLabel.pack(side="right")
        tk.Label(toolbarFrame, text="\t").pack(side="right")

        self.fig = mpl.figure.Figure()
        self.fig.patch.set_facecolor("#d9d9d9")
        self.dataCanvas = FigureCanvasTkAgg(self.fig, self.parent)

        # add toolbar to plot
        self.toolbar = NavigationToolbar2Tk(self.dataCanvas, toolbarFrame)
        self.toolbar.update()
        self.click = self.fig.canvas.mpl_connect("button_press_event", self.onpress)
        self.unclick = self.fig.canvas.mpl_connect("button_release_event", self.onrelease)

        # add axes for colormap sliders and reset button - leave invisible until rdata loaded
        self.ax_cmax = self.fig.add_axes([0.95, 0.55, 0.01, 0.30])
        self.ax_cmax.set_visible(False)
        self.ax_cmin  = self.fig.add_axes([0.95, 0.18, 0.01, 0.30])
        self.ax_cmin.set_visible(False)
        self.reset_ax = self.fig.add_axes([0.935, 0.11, 0.04, 0.03])
        self.reset_ax.set_visible(False)
        self.ax = self.fig.add_subplot(111)

        # initiate a twin axis that shows twtt
        self.secaxy0 = self.ax.twinx()
        self.secaxy0.yaxis.set_ticks_position("left")
        self.secaxy0.yaxis.set_label_position("left")
        self.secaxy0.spines["left"].set_position(("outward", 52))

        # initiate a twin axis that shares the same x-axis and shows approximate depth
        self.secaxy1 = self.ax.twinx()
        self.secaxy1.yaxis.set_ticks_position("right")
        self.secaxy1.yaxis.set_label_position("right")

        # initiate a twin axis that shows along-track distance
        self.secaxx = self.ax.twiny()
        self.secaxx.xaxis.set_ticks_position("bottom")
        self.secaxx.xaxis.set_label_position("bottom")
        self.secaxx.spines["bottom"].set_position(("outward", 42))

        # set zorder of secondary axes to be behind main axis (self.ax)
        self.secaxx.set_zorder(-100)
        self.secaxy0.set_zorder(-100)
        self.secaxy1.set_zorder(-100)

        self.ax.set_visible(False)

        # connect xlim_change with event to update image background for blitting
        self.draw_cid = self.fig.canvas.mpl_connect("draw_event", self.update_bg)

        # create colormap sliders and reset button - initialize for data image
        self.s_cmin = mpl.widgets.Slider(self.ax_cmin, "min", 0, 1, orientation="vertical")
        self.s_cmax = mpl.widgets.Slider(self.ax_cmax, "max", 0, 1, orientation="vertical")
        self.cmap_reset_button = mpl.widgets.Button(self.reset_ax, "reset", color="lightgoldenrodyellow")
        self.cmap_reset_button.on_clicked(self.cmap_reset)

        
    # set_vars is a method to set impick variables
    def set_vars(self):
        self.f_saveName = ""
        self.dtype = "amp"
        self.basemap = None
        self.pick_surf = None

        self.pick_state = False
        self.pick_segment = 0

        self.data_cmin = None
        self.data_cmax = None
        self.clut_cmin = None
        self.clut_cmax = None

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
        self.clut_imSwitch_flag = False
        self.surf_pickFlag = False
        self.edit_flag = False

        self.edit_segmentNum = 0
        self.im_status.set("data")
        self.pick_vis.set(True)
        self.pick_ann_vis.set(False)
        self.debugState = False
        self.pickLabel.config(fg="#d9d9d9")
        self.secaxx.set_xlabel("along-track distance [m]")
        self.secaxy0.set_ylabel("two-way travel time [microsec.]")
        self.secaxx.set_visible(True)


    # get debug state from gui settings
    def set_debugState(self, debugState):
        self.debugState = debugState


    # load calls ingest() on the data file and sets the datacanvas
    def load(self, rdata):       
        # receive the rdata
        self.rdata = rdata

        # set scalebar axes now that data displayed
        self.ax.set_visible(True)
        self.ax_cmax.set_visible(True)
        self.ax_cmin.set_visible(True)
        self.reset_ax.set_visible(True)
        
        # set figure title and axes labels
        self.ax.set_title(self.rdata.fpath.split("/")[-1].split(".")[0])
        self.ax.set(xlabel = "trace", ylabel = "sample")

        # Get data display window size in inches
        w,h = self.fig.get_size_inches()*self.fig.dpi

        # Choose pyramid
        p = -1
        for i in range(len(self.rdata.dPyramid)-1, -1, -1):
            if(self.rdata.dPyramid[i].shape[0] > h):
                p = i
                break

        print(i)
        
        # calculate power of rdata
        #Pow_data = np.power(self.rdata.proc_data,2)
        Pow_data = np.power(self.rdata.dPyramid[p],2)
        # replace zero power values with nan
        Pow_data[Pow_data == 0] = np.nan
        # dB it
        self.dB_data = np.log10(Pow_data)

        # get clutter data in dB
        # check if clutter data is stored in linear space or log space - lin space should have values less than 1
        # if in lin space, convert to dB
        if (np.nanmax(np.abs(self.rdata.clut)) < 1) or (~np.all(self.rdata.clut == 1)):
            # calculate power (squared amplitude)
            #Pow_clut = np.power(self.rdata.clut,2)
            Pow_clut = np.power(self.rdata.cPyramid[p],2)
            # replace zero power values with nan
            Pow_clut[Pow_clut == 0] = np.nan
            # dB it
            self.dB_clut = np.log10(Pow_clut)
        # if in log space, leave as is
        else:
            self.dB_clut = self.rdata.clut

        # cut off rdata at 10th percentile to avoid extreme outliers - round down
        self.mindB_data = np.floor(np.nanpercentile(self.dB_data,10))
        self.mindB_clut = np.floor(np.nanpercentile(self.dB_clut,10))
        self.maxdB_data = np.nanmax(self.dB_data)
        self.maxdB_clut = np.nanmax(self.dB_clut)

        # reset samples missing data to small negative value for color scale consistency
        self.dB_data[np.isnan(self.dB_data)] = -9999
        self.dB_clut[np.isnan(self.dB_clut)] = -9999

        self.dataCanvas.get_tk_widget().pack(in_=self.dataFrame, side="bottom", fill="both", expand=1) 

        # display image data for radargram and clutter sim
        self.im_data  = self.ax.imshow(self.dB_data, cmap="Greys_r", aspect="auto", extent=[0, 
                        self.rdata.tnum - 1, self.rdata.snum - 1, 0])
        self.im_clut  = self.ax.imshow(self.dB_clut, cmap="Greys_r", aspect="auto", extent=[0, 
                        self.rdata.tnum - 1, self.rdata.snum - 1, 0])
        # update colormaps
        self.im_data.set_clim([self.mindB_data, self.maxdB_data])
        self.im_clut.set_clim([self.mindB_clut, self.maxdB_clut])

        # set slider bounds
        self.s_cmin.valmin = self.mindB_data - 10
        self.s_cmin.valmax = self.mindB_data + 10
        self.s_cmin.valinit = self.mindB_data
        self.s_cmax.valmin = self.maxdB_data - 10
        self.s_cmax.valmax = self.maxdB_data + 10
        self.s_cmax.valinit = self.maxdB_data

        self.update_slider()

        # set clutter sim visibility to false
        self.im_clut.set_visible(False)

        # initialize arrays to hold saved picks
        self.xln_surf_saved = np.repeat(np.nan, self.rdata.tnum)
        self.yln_surf_saved = np.repeat(np.nan, self.rdata.tnum)
        self.xln_subsurf_saved = np.repeat(np.nan, self.rdata.tnum)
        self.yln_subsurf_saved = np.repeat(np.nan, self.rdata.tnum)

        # initialize lines to hold existing picks
        if np.any(self.rdata.pick.existing.twtt_surf):
            self.existing_surf_ln = self.ax.plot(np.arange(self.rdata.tnum), utils.twtt2sample(self.rdata.pick.existing.twtt_surf, self.rdata.dt), "c")
        count = len(self.rdata.pick.existing.twtt_subsurf.items())
        if count > 0:
            x,y = zip(*self.rdata.pick.existing.twtt_subsurf.items())
            y = np.hstack(y)
            x = np.repeat(np.arange(self.rdata.tnum), count)
            self.existing_subsurf_ln = self.ax.plot(x, utils.twtt2sample(y, self.rdata.dt), "b")

        # initialize lines to hold current pick segments
        self.tmp_surf_ln, = self.ax.plot(self.xln_surf,self.yln_surf,"mx")                          # empty line for surface pick segment
        self.saved_subsurf_ln, = self.ax.plot(self.xln_subsurf_saved,self.yln_subsurf_saved,"g")    # empty line for saved subsurface pick
        self.tmp_subsurf_ln, = self.ax.plot(self.xln_subsurf,self.yln_subsurf,"rx")                 # empty line for current pick segment
        self.saved_surf_ln, = self.ax.plot(self.xln_surf_saved, self.yln_subsurf_saved, "y")        # plot lidar surface

        # update the canvas
        self.dataCanvas._tkcanvas.pack()
        self.dataCanvas.draw()

        # update toolbar to save axes extents
        self.toolbar.update()


    # get_pickState is a method to return the current picking state
    def get_pickState(self):
        return self.pick_state


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
                self.rdata.pick.current.subsurf[str(self.pick_segment)] = np.repeat(np.nan, self.rdata.tnum)

            elif self.pick_state == False and self.edit_flag == False:
                if len(self.xln_subsurf) >=  2:
                    self.pick_segment += 1
                    self.pickLabel.config(text="subsurface pick segment " + str(self.pick_segment - 1) + ":\t inactive", fg="black")
                # if surface pick layer has only one pick, remove
                else:
                    self.clear_last()
                    del self.rdata.pick.current.subsurf[str(self.pick_segment)]
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
                    # Set surf_pickFlag to True to show that a surface pick has been made
                    self.surf_pickFlag = True

                self.blit()

            # pass pick trace location to basemap
            if self.basemap and self.basemap.get_state() == 1:
                self.basemap.plot_idx(self.pick_trace)

            # if in debug state, print pick info
            if self.debugState == True:
                utils.print_pickInfo(self.rdata, self.pick_trace, pick_sample)


    # pick_interp is a method for cubic spline interpolation of twtt between pick locations
    def pick_interp(self,surf = None):
        # if there are at least two picked points, interpolate
        try:
            if surf == "subsurface":
                if len(self.xln_subsurf) >= 2:                   
                    # cubic spline between picks
                    cs = CubicSpline(self.xln_subsurf, self.yln_subsurf)
                    # generate array between first and last pick indices on current layer
                    picked_traces = np.arange(self.xln_subsurf[0], self.xln_subsurf[-1] + 1)
                    sample = cs(picked_traces).astype(int)
                    # add cubic spline output interpolation to pick dictionary - force output to integer for index of pick
                    if self.edit_flag == True:
                        self.rdata.pick.current.subsurf[str(self.layerVar.get())][picked_traces] = sample
                        # add pick interpolation to saved pick array
                        self.xln_subsurf_saved[picked_traces] = picked_traces
                        self.yln_subsurf_saved[picked_traces] = sample
                        self.edit_flag = False
                    else:
                        self.rdata.pick.current.subsurf[str(self.pick_segment - 1)][picked_traces] = cs(picked_traces).astype(int)
                        # add pick interpolation to saved pick array
                        self.xln_subsurf_saved[picked_traces] = picked_traces
                        self.yln_subsurf_saved[picked_traces] = sample    

            elif surf == "surface":
                if len(self.xln_surf) >= 2:
                    # cubic spline between surface picks
                    cs = CubicSpline(self.xln_surf,self.yln_surf)
                    # generate array between first and last pick indices on current layer
                    picked_traces = np.arange(self.xln_surf[0], self.xln_surf[-1] + 1)
                    sample = cs(picked_traces).astype(int)
                    # input cubic spline output surface twtt array - force output to integer for index of pick
                    self.rdata.pick.current.surf[picked_traces] = sample
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


    def clear_picks(self, surf = None):
        # clear all picks
        if surf == "subsurface":
            if len(self.xln_subsurf) + np.count_nonzero(~np.isnan(self.xln_subsurf_saved)) > 0:
                # set picking state to false
                if self.pick_state == True and self.pick_surf == "subsurface":
                    self.set_pickState(False,surf="subsurface")
                # delete pick lists
                self.yln_subsurf_saved[:] = np.nan
                self.xln_subsurf_saved[:] = np.nan
                # clear current subsurf picks dictionary
                self.rdata.pick.current.subsurf.clear()
                self.rdata.pick.current.subsurf_opt.clear()
                # reset pick segment increment to 0
                self.pick_segment = 0
                self.pickLabel.config(fg="#d9d9d9")
                self.layerVar.set(self.pick_segment)
                # remove pick annotations
                for _i in self.ann_list:
                    _i.remove()
                del self.ann_list[:]

        elif surf == "surface":
            self.rdata.pick.current.surf.fill(np.nan)
            self.surf_pickFlag = False


    def clear_last(self):
        # clear last pick
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
                    self.surf_pickFlag = False


    def edit_pkLayer(self):
        layer = self.layerVar.get()
        if (len(self.rdata.pick.current.subsurf) > 0) and (self.edit_flag == False) and (not ((self.pick_state == True) and (self.pick_surf == "subsurface") and (layer == self.pick_segment))) and (tk.messagebox.askokcancel("warning", "edit pick segment " + str(layer) + "?", icon = "warning") == True):
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
            picks_idx = np.where(~np.isnan(self.rdata.pick.current.subsurf[str(layer)]))[0]
            # return picked traces to xln list
            self.xln_subsurf = picks_idx[::100].tolist()
            # return picked samples to yln list
            self.yln_subsurf = self.rdata.pick.current.subsurf[str(layer)][picks_idx][::100].tolist()
            # clear saved picks
            self.xln_subsurf_saved[picks_idx] = np.nan
            self.yln_subsurf_saved[picks_idx] = np.nan
            self.rdata.pick.current.subsurf[str(layer)][picks_idx] = np.nan
            # reset plotted lines
            self.tmp_subsurf_ln.set_data(self.xln_subsurf, self.yln_subsurf)
            self.saved_subsurf_ln.set_data(self.xln_subsurf_saved, self.yln_subsurf_saved)
            # remove pick annotation
            self.ann_list[layer].remove()
            del self.ann_list[layer]
            # update pick label
            self.pickLabel.config(text="subsurface pick segment " + str(layer) + ":\t active", fg="red")
            self.blit()


    def delete_pkLayer(self):
        layer = self.layerVar.get()
        # delete selected pick segment
        if (len(self.rdata.pick.current.subsurf) > 0) and (tk.messagebox.askokcancel("warning", "delete pick segment " + str(layer) + "?", icon = "warning") == True):
            # if picking active and only one segment exists, clear all picks
            if (self.pick_state == True) and (len(self.rdata.pick.current.subsurf) == 1):
                self.clear_picks(surf = "subsurface")
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
                    picks_idx = np.where(~np.isnan(self.rdata.pick.current.subsurf[str(layer)]))[0]
                    # remove picks from plot list
                    self.xln_subsurf_saved[picks_idx] = np.nan
                    self.yln_subsurf_saved[picks_idx] = np.nan
                    self.saved_subsurf_ln.set_data(self.xln_subsurf_saved ,self.yln_subsurf_saved)

                # delete pick dict layer
                del self.rdata.pick.current.subsurf[str(layer)]

                # remove pick annotation
                self.ann_list[layer].remove()
                del self.ann_list[layer]
                
                # roll back pick segment counter
                if self.pick_segment >=1:
                    self.pick_segment -= 1 

                # reorder pick layers if necessary
                if layer != len(self.rdata.pick.current.subsurf):
                    for _i in range(layer, len(self.rdata.pick.current.subsurf)):
                        self.rdata.pick.current.subsurf[str(_i)] = np.copy(self.rdata.pick.current.subsurf[str(_i + 1)])
                        # reorder annotations
                        self.ann_list[_i].set_text(str(_i))

                    del self.rdata.pick.current.subsurf[str(_i + 1)]

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
                self.layerVar.set(0)
            self.update_option_menu()
            self.update_bg()


    def show_pickLabels(self):
        if self.pick_ann_vis.get() == True:
            for _i in self.ann_list:
                _i.set_visible(True)
                self.update_bg()
        else:
            for _i in self.ann_list:
                _i.set_visible(False)
                self.update_bg()


    # add_pickLabels is a method to create annotations for picks
    def add_pickLabels(self):
        if len(self.ann_list) < self.pick_segment:
            # get x and y locations for placing annotation
            x = np.where(~np.isnan(self.rdata.pick.current.subsurf[str(self.pick_segment - 1)]))[0][0]
            y = self.rdata.pick.current.subsurf[str(self.pick_segment - 1)][x]
            ann = self.ax.text(x-75,y+75, str(self.pick_segment - 1), bbox=dict(facecolor='white', alpha=0.5), horizontalalignment='right', verticalalignment='top')
            self.ann_list.append(ann)
            if self.pick_ann_vis.get() == False:
                ann.set_visible(False)


    # remove_imported_picks is a method to remove any imported data file picks from the image
    def remove_imported_picks(self):
        if len(self.ax.lines) > 4:
            for _i in range(len(self.ax.lines) - 4):
                self.ax.lines[-1].remove()


    def show_data(self):
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
        self.s_cmax.valmin = self.maxdB_data - 10
        self.s_cmax.valmax = self.maxdB_data + 10
        self.update_slider()
        # reverse visilibilty
        self.im_clut.set_visible(False)
        self.im_data.set_visible(True)
        # redraw canvas
        self.fig.canvas.draw()
        self.im_status.set("data")


    def show_clut(self):
        # toggle to clutter sim viewing
        # get radar data colormap slider values for reviewing
        self.data_cmin = self.s_cmin.val
        self.data_cmax = self.s_cmax.val

        if not self.clut_imSwitch_flag:
            # if this is the first time viewing the clutter sim, set colorbar limits to initial values
            self.s_cmin.valinit = self.mindB_clut
            self.s_cmax.valinit = self.maxdB_clut
        else: 
            # if clutter has been shown before revert to previous colorbar values
            self.im_clut.set_clim([self.clut_cmin, self.clut_cmax])
            self.s_cmin.valinit = self.clut_cmin
            self.s_cmax.valinit = self.clut_cmax

        self.s_cmin.valmin = self.mindB_clut - 10
        self.s_cmin.valmax = self.mindB_clut + 10            
        self.s_cmax.valmin = self.maxdB_clut - 10
        self.s_cmax.valmax = self.maxdB_clut + 10
        self.update_slider()
        # reverse visilibilty
        self.im_data.set_visible(False)
        self.im_clut.set_visible(True)
        # set flag to indicate that clutter has been viewed for resetting colorbar limits
        self.clut_imSwitch_flag = True    
        # redraw canvas
        self.fig.canvas.draw()
        self.im_status.set("clut")


    # pick_vis is a method to toggle the visibility of picks
    def show_picks(self):
        self.show_artists()
        self.safe_draw()
        self.fig.canvas.blit(self.ax.bbox)


    def hide_picks(self):
        self.hide_artists()
        self.safe_draw()
        self.fig.canvas.blit(self.ax.bbox)


    # update the pick layer menu based on how many layers exist
    def update_option_menu(self):
            menu = self.layerMenu["menu"]
            menu.delete(0, "end")
            for _i in range(self.pick_segment):
                menu.add_command(label=_i,
                    command=tk._setit(self.layerVar,_i))


    def update_slider(self):
        self.ax_cmax.clear()
        self.ax_cmin.clear()
        self.s_cmin.__init__(self.ax_cmin, "min", valmin=self.s_cmin.valmin, valmax=self.s_cmin.valmax, valinit=self.s_cmin.valinit, orientation="vertical")
        self.s_cmax.__init__(self.ax_cmax, "max", valmin=self.s_cmax.valmin, valmax=self.s_cmax.valmax, valinit=self.s_cmax.valinit, orientation="vertical")
        self.s_cmin.on_changed(self.cmap_update)
        self.s_cmax.on_changed(self.cmap_update)


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
        except Exception as err:
            print("cmap_update error: " + str(err))


    def cmap_reset(self, event):
        # reset sliders to initial values
        if self.im_data.get_visible():
            self.s_cmin.valmin = self.mindB_data - 10
            self.s_cmin.valmax = self.mindB_data + 10
            self.s_cmin.valinit = self.mindB_data
            self.s_cmax.valmin = self.maxdB_data - 10
            self.s_cmax.valmax = self.maxdB_data + 10
            self.s_cmax.valinit = self.maxdB_data
        else:
            # if clutter is displayed, change slider bounds
            self.s_cmin.valmin = self.mindB_clut - 10
            self.s_cmin.valmax = self.mindB_clut + 10
            self.s_cmin.valinit = self.mindB_clut
            self.s_cmax.valmin = self.maxdB_clut - 10
            self.s_cmax.valmax = self.maxdB_clut + 10
            self.s_cmax.valinit = self.maxdB_clut
        self.update_slider()
        self.cmap_update()


    # temporarily disconnect the draw_event callback to avoid recursion
    def safe_draw(self):
        canvas = self.fig.canvas
        canvas.mpl_disconnect(self.draw_cid)
        canvas.draw()
        self.draw_cid = canvas.mpl_connect("draw_event", self.update_bg)


    # hide plotted lines
    def hide_artists(self):
        for _i in self.ax.lines:
            _i.set_visible(False)


    # show plotted lines
    def show_artists(self):
        for _i in self.ax.lines:
            _i.set_visible(True)


    # when the figure is resized, hide picks, draw everything, and update the background.
    def update_bg(self, event=None):
        self.hide_artists()
        self.safe_draw()
        self.axbg = self.dataCanvas.copy_from_bbox(self.ax.bbox)
        self.show_artists()
        self.blit()


    # update the figure, without needing to redraw the "axbg" artists.
    def blit(self):
        self.fig.canvas.restore_region(self.axbg)
        for _i in self.ax.lines:
            self.ax.draw_artist(_i)
        self.fig.canvas.blit(self.ax.bbox)


    # saveWarning is a method which checks if picks exist or if the user would like to discard existing picks before moving to the next track
    def saveWarning(self):
        # check if picks have been made and saved
        if ((self.get_subsurfPickFlag() == True) or (self.surf_pickFlag == True)) and (self.f_saveName == ""):
            if tk.messagebox.askyesno("Warning", "Load next track without saving picks?", icon = "warning") == True:
                return True
        else: 
            return True


    # clear_canvas is a method to clear the data canvas and figures to reset app
    def clear_canvas(self):
        # clearing individual axis objects seems to keep a history of these objects and causes axis limit issues when opening new track
        self.ax.cla()


    # get_subsurfPickFlag is a method which returns true if manual subsurface picks exist, and false otherwise   
    def get_subsurfPickFlag(self):
        if len(self.xln_subsurf) + np.count_nonzero(~np.isnan(self.xln_subsurf_saved)) > 0:
            return True
        else:
            return False


    # get_surfPickFlag is a method which returns true if manual surface picks exist, and false otherwise
    def get_surfPickFlag(self):
        return self.surf_pickFlag


    # get_numPkLyrs is a method to return the number of picking layers which exist
    def get_numPkLyrs(self):
        return len(self.rdata.pick.current.subsurf)


    # set_picks is a method to update the saved pick arrays based on current the picking dictionary
    def set_picks(self):
        # reset yln_saved arrays to replace with new dictionary values for replotting
        self.yln_surf_saved.fill(np.nan)
        self.yln_subsurf_saved.fill(np.nan)
        idx = np.where(~np.isnan(self.rdata.pick.current.surf))[0]
        self.yln_surf_saved[idx] = self.rdata.pick.current.surf[idx]
        for _i in range(len(self.rdata.pick.current.subsurf)):
            idx = np.where(~np.isnan(self.rdata.pick.current.subsurf[str(_i)]))[0]
            self.yln_subsurf_saved[idx] = self.rdata.pick.current.subsurf[str(self.pick_segment - 1)][idx]


    # set axis labels
    def set_axes(self, eps_r, cmap):
        self.ax.set_xlim(0, self.rdata.tnum)
        self.ax.set_ylim(self.rdata.snum, 0)

        # update twtt and depth (subradar dist.)
        if self.rdata.dt < 1e-9:
            self.secaxy0.set_ylabel("two-way travel time [nanosec.]")
            self.secaxy0.set_ylim(self.rdata.snum * self.rdata.dt * 1e9, 0)
        else:
            self.secaxy0.set_ylim(self.rdata.snum * self.rdata.dt * 1e6, 0)

        self.secaxy1.set_ylabel("approx. subradar distance [m] ($\epsilon_{}$ = {}".format("r",eps_r))
        self.secaxy1.set_ylim(utils.twtt2depth(self.rdata.snum * self.rdata.dt, eps_r), 0)

        # update along-track distance
        if not np.all(np.isnan(self.rdata.navdf["dist"])) or  np.all((self.rdata.navdf["dist"] == 0)):
            # use km if distance exceeds 1 km
            if self.rdata.navdf.iloc[-1]["dist"] >= 1e3:
                self.secaxx.set_xlabel("along-track distance [km]")
                self.secaxx.set_xlim(0, self.rdata.navdf.iloc[-1]["dist"]*1e-3)

            else:
                self.secaxx.set_xlim(0, self.rdata.navdf.iloc[-1]["dist"])
        
        else:
            self.secaxx.set_visible(False)
        
        self.im_data.set_cmap(cmap)
        self.im_clut.set_cmap(cmap)

        self.dataCanvas.draw()


    # get_nav method returns the nav data       
    def get_nav(self):
        return self.rdata.nav


    # set_im is a method to set which rdata is being displayed
    def set_im(self):
        if self.im_status.get() == "data":
            self.show_clut()

        elif self.im_status.get() =="clut":
            self.show_data()


    # get_basemap is a method to hold the basemap object passed from gui
    def get_basemap(self, basemap):
        self.basemap = basemap


    # save is a method to receive the pick save location from gui and save using utils.save
    def save(self, f_saveName, eps_r, cmap, figSize):
        self.f_saveName = f_saveName
        # zoom out to full rgram extent to save pick image
        self.set_axes(eps_r, cmap)
        if self.im_status.get() =="clut":
            self.show_data()
        # temporarily turn sliders to invisible for saving image
        self.ax_cmax.set_visible(False)
        self.ax_cmin.set_visible(False)
        self.reset_ax.set_visible(False)
        # hide pick annotations
        self.pick_ann_vis.set(False)
        self.show_pickLabels()        
        # ensure picks are visible
        self.pick_vis.set(True)
        self.show_picks()
        w,h = self.fig.get_size_inches()    # get pre-save figure size
        self.fig.set_size_inches((float(figSize[0]),float(figSize[1])))    # set figsize to wide aspect ratio
        utils.exportIm(f_saveName, self.fig)
        # return figsize to intial values and make sliders visible again
        self.fig.set_size_inches((w,h))
        self.ax_cmax.set_visible(True)
        self.ax_cmin.set_visible(True)
        self.reset_ax.set_visible(True)
        self.update_bg()


    # onpress gets the time of the button_press_event
    def onpress(self,event):
        self.time_onclick = time.time()


    # onrelease calls addseg() if the time between the button press and release events
    # is below a threshold so that segments are not drawn while trying to zoom or pan
    def onrelease(self,event):
        if event.inaxes == self.ax:
            if event.button == 1 and ((time.time() - self.time_onclick) < 0.25):
                self.addseg(event)