###IMPORTS###
import utils, basemap
import h5py
import numpy as np
import tkinter as tk
import sys,os,time,copy
import matplotlib as mpl
mpl.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from scipy.interpolate import CubicSpline


class imPick(tk.Frame):
    # imPick is a class to pick horizons from a radar image
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
        radarRadio = tk.Radiobutton(infoFrame, text="Radargram", variable=self.im_status, value="data",command=self.show_data)
        radarRadio.pack(side="left")
        clutterRadio = tk.Radiobutton(infoFrame,text="Cluttergram", variable=self.im_status, value="clut",command=self.show_clut)
        clutterRadio.pack(side="left")
        
        deleteButton = tk.Button(toolbarFrame, text="Delete", command=self.delete_pkLayer).pack(side="right")
        # editButton = tk.Button(toolbarFrame, text="Edit", command=self.edit_pkLayer).pack(side="right")
        self.layerVar = tk.IntVar()
        self.layers=[0]
        self.layerMenu = tk.OptionMenu(toolbarFrame, self.layerVar, *self.layers)
        self.layerMenu.pack(side="right",pady=0)
        self.layerMenu["highlightthickness"]=0

        self.pickLabel = tk.Label(infoFrame, text="Subsurface Pick Segment:\t0", fg="#d9d9d9")#, font="-weight bold")
        self.pickLabel.pack(side="right")

        self.fig = mpl.figure.Figure()
        self.fig.patch.set_facecolor("#d9d9d9")
        self.dataCanvas = FigureCanvasTkAgg(self.fig, self.parent)
        # self.dataCanvas.get_tk_widget().pack(in_=dataFrame, side="bottom", fill="both", expand=1)
        # add toolbar to plot
        self.toolbar = NavigationToolbar2Tk(self.dataCanvas, toolbarFrame)
        self.toolbar.update()
        self.click = self.fig.canvas.mpl_connect("button_press_event", self.onpress)
        self.unclick = self.fig.canvas.mpl_connect('button_release_event', self.onrelease)


        # add axes for colormap sliders and reset button - leave invisible until data loaded
        self.ax_cmax = self.fig.add_axes([0.95, 0.55, 0.01, 0.30])
        self.ax_cmax.set_visible(False)
        self.ax_cmin  = self.fig.add_axes([0.95, 0.18, 0.01, 0.30])
        self.ax_cmin.set_visible(False)
        self.reset_ax = self.fig.add_axes([0.935, 0.11, 0.04, 0.03])
        self.reset_ax.set_visible(False)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_visible(False)

        # connect xlim_change with event to update image background for blitting
        # self.ax.callbacks.connect('xlim_changed', self.update_bg)
        self.draw_cid = self.fig.canvas.mpl_connect('draw_event', self.update_bg)

        # create colormap sliders and reset button - initialize for data image
        self.s_cmin = mpl.widgets.Slider(self.ax_cmin, 'min', 0, 1, orientation="vertical")
        self.s_cmax = mpl.widgets.Slider(self.ax_cmax, 'max', 0, 1, orientation="vertical")
        self.cmap_reset_button = mpl.widgets.Button(self.reset_ax, 'Reset', color="lightgoldenrodyellow")
        self.cmap_reset_button.on_clicked(self.cmap_reset)


    # set_vars is a method to set imPick variables
    def set_vars(self):
        self.pickLabel.config(text="Subsurface Pick Segment:\t0", fg="#d9d9d9")
        self.data_imSwitch_flag = ""
        self.clut_imSwitch_flag = ""
        self.f_loadName = ""
        self.f_saveName = ""
        self.dtype = "amp"
        self.press = False
        self.basemap = None
        self.pick_dict = {}
        self.pick_dict_opt = {}
        self.pick_idx = None
        self.pick_state = False
        self.pick_segment = 0
        self.data_cmin = None
        self.data_cmax = None
        self.clut_cmin = None
        self.clut_cmax = None
        # empty fields for picks
        self.xln_old = []
        self.yln_old = []
        self.xln = []
        self.yln = []
        self.xln_surf = []
        self.yln_surf = []
        self.surf = None
        self.pick = None
        self.saved_pick = None
        self.surf_pick = None
        self.im_status.set("data")


    # load calls ingest() on the data file and sets the datacanvas
    def load(self,f_loadName, data):
        self.f_loadName = f_loadName
        print('----------------------------------------')
        print("Loading: " + self.f_loadName)
        # receive the data
        self.data = data

        # create sample time array 
        self.sampleTime = np.arange(0,self.data["num_sample"]+1)*self.data["dt"]

        # set scalebar axes now that data displayed
        self.ax.set_visible(True)
        self.ax_cmax.set_visible(True)
        self.ax_cmin.set_visible(True)
        self.reset_ax.set_visible(True)

        # label axes    
        self.ax.set(xlabel = "along-track distance [km]", ylabel = "two-way travel time [microsec.]")
        
        # set figure title
        self.ax.set_title(os.path.splitext(self.f_loadName.split("/")[-1])[0])

        # calculate power of data
        Pow_data = np.power(self.data["amp"],2)
        # place data in dB for visualization
        self.dB_data = np.log(Pow_data)
        
        # get clutter data in dB for visualization
        # check if clutter data exists
        if np.any(self.data["clutter"]):
            # check if clutter data is storede in linear space or log space - lin space should have values less than 1
            # if in lin space, convert to dB
            if np.nanmax(np.abs(self.data["clutter"])) < 1:
                Pow_clut = np.power(self.data["clutter"],2)
                self.dB_clut = np.log(Pow_clut)
            # if in log space, leave as is
            else:
                self.dB_clut = self.data["clutter"]
            # replace any negative infinity clutter values with nan
            try:
                self.dB_clut[np.where(self.dB_clut == -np.inf)] = np.NaN
            except:
                pass
        # if no clutter data, use empty array
        else:
            self.dB_clut = self.data["clutter"]
            

        # cut off data at 10th percentile to avoid extreme outliers - round down
        self.mindB_data = np.floor(np.nanpercentile(self.dB_data,10))
        self.mindB_clut = np.floor(np.nanpercentile(self.dB_clut,10))
        
        self.maxdB_data = np.nanmax(self.dB_data)
        self.maxdB_clut = np.nanmax(self.dB_clut)
        # self.maxdB_clut = np.floor(np.nanpercentile(self.dB_clut,90))
        # print(self.mindB_data,self.maxdB_data)
        # print(self.mindB_clut,self.maxdB_clut)

        self.surf, = self.ax.plot(self.data["dist"],self.data["twtt_surf"]*1e6,"c")     # line for twtt surface
        self.pick, = self.ax.plot([],[],"rx")                                    # empty line for current pick
        self.saved_pick = self.ax.scatter([],[],c="g",marker=".",s=8,linewidth=0)   # empty line for saved pick
        self.surf_pick, = self.ax.plot([],[],"mx")

        self.dataCanvas.get_tk_widget().pack(in_=self.dataFrame, side="bottom", fill="both", expand=1) 
             
        # display image data for radargram and clutter sim
        self.im_data  = self.ax.imshow(self.dB_data, cmap="gray", aspect="auto", extent=[self.data["dist"][0], 
                        self.data["dist"][-1], self.data["amp"].shape[0] * self.data["dt"] * 1e6, 0])
        self.im_clut  = self.ax.imshow(self.dB_clut, cmap="gray", aspect="auto", extent=[self.data["dist"][0], 
                        self.data["dist"][-1], self.data["amp"].shape[0] * self.data["dt"] * 1e6, 0])

        # the first time the amplitude image is loaded, update colormap to cut off values below 10th percentile
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

        # update the canvas
        self.dataCanvas._tkcanvas.pack()
        self.dataCanvas.draw()

        # save background
        self.update_bg()

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
                if len(self.xln) >= 2:
                    self.pick_segment += 1
                # if current layer has only one pick, remove
                else:
                    self.clear_last()
                self.pickLabel.config(text="Subsurface Pick Segment:\t" + str(self.pick_segment), fg="#008000")  
                # initialize pick index and twtt dictionaries for current picking layer
                self.pick_dict["segment_" + str(self.pick_segment)] = np.ones(self.data["num_trace"])*-1
            elif self.pick_state == False:
                if len(self.xln) >=  2:
                    self.pick_segment += 1
                    # only advance pick segment if picks made on previous layer
                self.pickLabel.config(fg="#FF0000")


    # addseg is a method to for user to generate picks
    def addseg(self, event):
        if self.f_loadName:
            # find nearest index to event.xdata
            self.pick_idx_x1 = utils.find_nearest(self.data["dist"], event.xdata)
            # round event.ydata to nearest index
            pick_idx_y1 = int(round(event.ydata*1e-6/self.data["dt"]))
            # check if picking state is a go
            if self.pick_state == True:
                # restrict subsurface picks to fall below surface
                if (self.pick_surf == "subsurface") and (event.ydata*1e-6 > self.data["twtt_surf"][self.pick_idx_x1]) or (np.isnan(self.data["twtt_surf"][self.pick_idx_x1])):
                # make sure pick falls after previous pick
                    if (len(self.xln) >= 1) and (self.pick_idx_x1 <= self.xln[-1]):
                        pass
                    else:
                        self.xln.append(self.pick_idx_x1)
                        self.yln.append(pick_idx_y1)
                        self.pick.set_data(self.xln, self.yln)
                elif self.pick_surf == "surface":
                    if (len(self.xln_surf) >= 1) and (self.pick_idx_x1 <= self.xln_surf[-1]):
                        pass
                    else:
                        self.xln_surf.append(self.pick_idx_x1)
                        self.yln_surf.append(pick_idx_y1)
                        self.surf_pick.set_data(self.xln_surf, self.yln_surf)
                self.blit()

            # plot pick location to basemap
            if self.basemap and self.basemap.get_state() == 1:
                self.basemap.plot_idx(self.pick_idx_x1)


    # pick_interp is a method for cubic spline interpolation of twtt between pick locations
    def pick_interp(self,surf = None):
        # if there are at least two picked points, interpolate
        try:
            if surf == "subsurface":
                if len(self.xln) >= 2:
                    # cubic spline between picks
                    cs = CubicSpline(self.xln,self.yln)
                    # get the first pick x-position for current layer
                    pick_idx_x0 = utils.find_nearest(self.data["dist"], self.xln[0])
                    # generate array between first and last pick indices on current layer
                    pick_idx = np.arange(pick_idx_x0,self.pick_idx_x1 + 1)
                    # add cubic spline output interpolation to pick dictionary
                    self.pick_dict["segment_" + str(self.pick_segment - 1)][pick_idx] = cs(self.data["dist"][pick_idx])
                    # add pick interpolation to saved pick list
                    self.xln_old.extend(self.data["dist"][pick_idx])
                    self.yln_old.extend(self.pick_dict["segment_" + str(self.pick_segment - 1)][pick_idx])


            elif surf == "surface":
                if len(self.xln_surf) >= 2:
                    # cubic spline between surface picks
                    cs = CubicSpline(self.xln_surf,self.yln_surf)
                    # get the first pick x-position for current layer
                    pick_idx_x0 = utils.find_nearest(self.data["dist"], self.xln_surf[0])
                    # generate array between first and last pick indices on current layer
                    pick_idx = np.arange(pick_idx_x0,self.pick_idx_x1 + 1)
                    # input cubic spline output surface twtt array
                    self.data["twtt_surf"][pick_idx] = cs(self.data["dist"][pick_idx]) * 1e-6

        except Exception as err:
            print("Pick interp error: " + str(err))


    # plot_picks is a method to remove current pick list and add saved picks to plot
    def plot_picks(self, surf = None):
        if surf == "subsurface":
            # remove saved picks
            del self.xln[:]
            del self.yln[:]
            self.pick.set_data(self.xln, self.yln)
            self.saved_pick.set_offsets(np.c_[self.xln_old,self.yln_old])
        elif surf == "surface":
            del self.xln_surf[:]
            del self.yln_surf[:]
            self.surf_pick.set_data(self.xln_surf, self.yln_surf)
            self.surf.set_data(self.xln_surf,self.yln_surf)
            self.surf.set_data(self.data["dist"],self.data["twtt_surf"]*1e6)
            

    def clear_picks(self):
        # clear all picks
        if len(self.xln + self.xln_old) > 0 and tk.messagebox.askokcancel("Warning", "Clear all subsurface picks?", icon = "warning") == True:
            # delete pick lists
            del self.yln_old[:]
            del self.xln_old[:]
            # clear pick dictionary
            self.pick_dict.clear()
            # reset pick segment increment to 0
            self.pick_segment = 0
            self.pickLabel.config(text="Subsurface Pick Segment:\t" + str(self.pick_segment))


    def clear_last(self):
        # clear last pick
        if self.pick_state == True:
            if self.pick_surf == "subsurface" and len(self.xln) >= 1:
                del self.xln[-1:]
                del self.yln[-1:]
                # reset self.pick, then blit
                self.pick.set_data(self.xln, self.yln)
                self.blit()

            if self.pick_surf == "surface" and len(self.xln_surf) >= 1:
                del self.xln_surf[-1:]
                del self.yln_surf[-1:]
                # reset self.pick, then blit
                self.surf_pick.set_data(self.xln_surf, self.yln_surf)
                self.blit()


    def delete_pkLayer(self):
        # delete selected pick segment
        if (len(self.pick_dict) > 0) and (tk.messagebox.askokcancel("Warning", "Delete pick segment " + str(self.layerVar.get()) + "?", icon = "warning") == True):
            # find first pick location for segment
            first_idx = utils.find_nearest(np.asarray(self.xln_old), self.data["dist"][np.where(self.pick_dict["segment_" + str(self.layerVar.get())] != -1)[0][0]])
            # find last pick location for segment
            last_idx = utils.find_nearest(np.asarray(self.xln_old), self.data["dist"][np.where(self.pick_dict["segment_" + str(self.layerVar.get())] != -1)[0][-1]])
            # remove picks from plot list
            del self.xln_old[first_idx:last_idx + 1]
            del self.yln_old[first_idx:last_idx + 1]   
            # delete pick dict layer
            del self.pick_dict["segment_" + str(self.layerVar.get())]

            self.saved_pick.set_offsets(np.c_[self.xln_old,self.yln_old])
            
            self.pick_segment -= 1
            if self.pick_state == True:
                self.pickLabel.config(text="Subsurface Pick Segment:\t" + str(self.pick_segment))
            elif self.pick_state == False:
                self.pickLabel.config(text="Subsurface Pick Segment:\t" + str(self.pick_segment - 1))    

            # reorder pick layers
            if self.layerVar.get() != len(self.pick_dict):
                for _i in range(self.layerVar.get(), len(self.pick_dict)):
                    self.pick_dict["segment_" + str(_i)] = np.copy(self.pick_dict["segment_" + str(_i + 1)])
                del self.pick_dict["segment_" + str(_i + 1)]
            self.update_option_menu()
            self.blit()

    # def edit_pkLayer(self):
    #     # edit the selected pick layer
    #     if (len(self.pick_dict) > 0):
    #         print("----------\npick layer editing is currently in development - remove pick layer and repick for now.\n----------")

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
        self.s_cmin.__init__(self.ax_cmin, 'min', valmin=self.s_cmin.valmin, valmax=self.s_cmin.valmax, valinit=self.s_cmin.valinit, orientation="vertical")
        self.s_cmax.__init__(self.ax_cmax, 'max', valmin=self.s_cmax.valmin, valmax=self.s_cmax.valmax, valinit=self.s_cmax.valinit, orientation="vertical")
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


    def safe_draw(self):
        """temporarily disconnect the draw_event callback to avoid recursion"""
        canvas = self.fig.canvas
        canvas.mpl_disconnect(self.draw_cid)
        canvas.draw()
        self.draw_cid = canvas.mpl_connect('draw_event', self.update_bg)


    def update_bg(self, event=None):
        """
        when the figure is resized, hide picks, draw everything,
        and update the background.
        """
        if self.surf:
            self.surf.set_visible(False)
        if self.surf_pick:
            self.surf_pick.set_visible(False)
        if self.pick:
            self.pick.set_visible(False)
        if self.saved_pick:
            self.pick.set_visible(False)
        self.safe_draw()
        self.axbg = self.dataCanvas.copy_from_bbox(self.ax.bbox)
        if self.surf:
            self.surf.set_visible(True)
        if self.surf_pick:
            self.surf_pick.set_visible(True)
        if self.pick:
            self.pick.set_visible(True)
        if self.saved_pick:
            self.pick.set_visible(True)
        self.blit()


    def blit(self):
        """
        update the figure, without needing to redraw the
        "axbg" artists.
        """
        self.fig.canvas.restore_region(self.axbg)
        if self.pick:
            self.ax.draw_artist(self.pick)
        if self.saved_pick:
            self.ax.draw_artist(self.saved_pick)
        if self.surf_pick:
            self.ax.draw_artist(self.surf_pick)
        if self.surf:
            self.ax.draw_artist(self.surf)
        self.fig.canvas.blit(self.ax.bbox)


    # nextSave_warning is a method which checks if picks exist or if the user would like to discard existing picks before moving to the next track
    def nextSave_warning(self):
        # check if picks have been made and saved
        if len(self.xln + self.xln_old) > 0 and self.f_saveName == "":
            if tk.messagebox.askokcancel("Warning", "Load next track without saving picks?", icon = "warning") == True:
                return True
        else: 
            return True


    # clear_canvas is a method to clear the data canvas and figures to reset app
    def clear_canvas(self):
        self.ax.cla()


    # get_pickLen is a method to return the length of existing picks
    def get_pickLen(self):
        return len(self.xln + self.xln_old)


    # get_numPkLyrs is a method to return the number of picking layers which exist
    def get_numPkLyrs(self):
        return len(self.pick_dict)


    # get_pickDict is a method to return the pick dictionary
    def get_pickDict(self):
        return self.pick_dict

    
    # set_picDict is a method to update the pick dictionary based on wvPick pick updates
    def set_pickDict(self, in_dict):
        if self.pick_dict:
            self.pick_dict_opt = in_dict
            # delete yln_old list to reset with new dictionary values for replotting
            del self.yln_old[:]
            for _i in range(len(self.pick_dict_opt)):
                picked_traces = np.where(self.pick_dict_opt["segment_" + str(_i)] != -1.)[0]
                self.yln_old.extend(self.pick_dict_opt["segment_" + str(_i)][picked_traces])



    # get_nav method returns the nav data       
    def get_nav(self):
        return self.data["navdat"]


    # get_idx is a method that reurns the trace index of a click event on the image
    def get_idx(self):
        return self.pick_idx_x1


    # set_im is a method to set which data is being displayed
    def set_im(self):
        if self.im_status.get() == "data":
            self.show_clut()

        elif self.im_status.get() =="clut":
            self.show_data()


    # get_basemap is a method to hold the basemap object passed from gui
    def get_basemap(self, basemap):
        self.basemap = basemap


    # save is a method to receive the pick save location from gui and save using utils.save
    def save(self, f_saveName):
        self.f_saveName = f_saveName
        utils.savePick(self.f_saveName, self.data, self.pick_dict)
        # zoom out to full rgram extent to save pick image
        self.ax.set_xlim((self.data["dist"][0], self.data["dist"][-1]))
        self.ax.set_ylim((self.data["amp"].shape[0] * self.data["dt"] * 1e6, 0))
        if self.im_status.get() =="clut":
            self.show_data()
        extent = self.ax.get_window_extent().transformed(self.fig.dpi_scale_trans.inverted())
        utils.exportIm(self.f_saveName, self.fig, extent)
        self.update_bg()


    # onpress gets the time of the button_press_event
    def onpress(self,event):
        self.time_onclick = time.time()


    # onrelease calls addseg() if the time between the button press and release events
    # is below a threshold so that segments aren't drawn while trying to zoom or pan
    def onrelease(self,event):
        if event.inaxes == self.ax:
            if event.button == 1 and ((time.time() - self.time_onclick) < 0.25):
                self.addseg(event)