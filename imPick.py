import ingester
import utils
import basemap
import h5py
import numpy as np
import tkinter as tk
from tkinter import ttk as ttk
import sys,os
import matplotlib as mpl
mpl.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

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
        self.im_status.set("data")
        

        self.pickLabel = tk.Label(infoFrame, text="Picking Layer:\t0", fg="#d9d9d9")
        self.pickLabel.pack(side="right")

        self.fig = mpl.figure.Figure()
        self.fig.patch.set_facecolor("#d9d9d9")
        self.dataCanvas = FigureCanvasTkAgg(self.fig, self.parent)
        # self.dataCanvas.get_tk_widget().pack(in_=dataFrame, side="bottom", fill="both", expand=1)
        # add toolbar to plot
        self.toolbar = NavigationToolbar2Tk(self.dataCanvas, toolbarFrame)
        self.toolbar.update()
        self.key = self.fig.canvas.mpl_connect("key_press_event", self.onkey)
        self.click = self.fig.canvas.mpl_connect("button_press_event", self.addseg)

        # add axes for colormap sliders and reset button - leave invisible until data loaded
        self.ax_cmax = self.fig.add_axes([0.95, 0.55, 0.01, 0.30])
        self.ax_cmax.set_visible(False)
        self.ax_cmin  = self.fig.add_axes([0.95, 0.18, 0.01, 0.30])
        self.ax_cmin.set_visible(False)
        self.reset_ax = self.fig.add_axes([0.935, 0.11, 0.04, 0.03])
        self.reset_ax.set_visible(False)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_visible(False)

        # create colormap sliders and reset button - initialize for data image
        self.s_cmin = mpl.widgets.Slider(self.ax_cmin, 'min', 0, 1, orientation="vertical")
        self.s_cmax = mpl.widgets.Slider(self.ax_cmax, 'max', 0, 1, orientation="vertical")
        self.cmap_reset_button = mpl.widgets.Button(self.reset_ax, 'Reset', color="lightgoldenrodyellow")
        self.cmap_reset_button.on_clicked(self.cmap_reset)


    # set_vars is a method to set imPick variables
    def set_vars(self):
        self.pickLabel.config(text="Picking Layer:\t0", fg="#d9d9d9")
        self.data_imSwitch_flag = ""
        self.clut_imSwitch_flag = ""
        self.f_loadName = ""
        self.f_saveName = ""
        self.dtype = "amp"
        self.basemap = None
        self.pick_dict = {}
        self.pick_idx = None
        self.pick_state = False
        self.pick_layer = 0
        self.data_cmin = None
        self.data_cmax = None
        self.clut_cmin = None
        self.clut_cmax = None
        # empty fields for picks
        self.xln_old = []
        self.yln_old = []
        self.xln = []
        self.yln = []
        self.pick = None
        self.saved_pick = None

    # load calls ingest() on the data file and sets the datacanvas
    def load(self, f_loadName):
        self.f_loadName = f_loadName
        print("Loading: " + self.f_loadName)
        # ingest the data
        self.igst = ingester.ingester("h5py")
        self.data = self.igst.read(self.f_loadName)

        # set scalebar axes now that data displayed
        self.ax.set_visible(True)
        self.ax_cmax.set_visible(True)
        self.ax_cmin.set_visible(True)
        self.reset_ax.set_visible(True)

        # set figure title
        self.ax.set_title(os.path.splitext(self.f_loadName.split("/")[-1])[0])

        # find max power in data to scale image
        self.data["clutter"][np.where(self.data["clutter"] == -np.inf)] = np.NaN
        maxPow_data = np.nanmax(np.power(self.data[self.dtype][:],2))
        maxPow_clut = np.nanmax(np.power(self.data["clutter"][:],2))

        # scale data in dB with maxPow value as the reference
        self.imScl_data = np.log(np.power(self.data[self.dtype],2) / maxPow_data)
        if np.any(self.data["clutter"]):
            self.imScl_clut = np.log(np.power(self.data["clutter"],2) / maxPow_clut)
        else:
            self.imScl_clut = self.data["clutter"]

        # cut off data at 10th percentile to avoid extreme outliers - round down
        self.mindB_data = np.floor(np.nanpercentile(self.imScl_data,10))
        self.mindB_clut = np.floor(np.nanpercentile(self.imScl_clut,10))
        self.surf, = self.ax.plot(self.data["dist"],self.data["twtt_surf"],"c")     # empty line for twtt surface
        self.pick, = self.ax.plot([],[],"r")                                        # empty line for current pick
        self.saved_pick = self.ax.scatter([],[],c="g",marker=".",s=8,linewidth=0)   # empty line for saved pick

        self.dataCanvas.get_tk_widget().pack(in_=self.dataFrame, side="bottom", fill="both", expand=1) 
             
        # display image data for radargram and clutter sim
        self.im_data  = self.ax.imshow(self.imScl_data, cmap="gray", aspect="auto", extent=[self.data["dist"][0], 
                        self.data["dist"][-1], self.data["amp"].shape[0] * self.data["dt"] * 1e6, 0])
        self.im_clut  = self.ax.imshow(self.imScl_clut, cmap="gray", aspect="auto", extent=[self.data["dist"][0], 
                        self.data["dist"][-1], self.data["amp"].shape[0] * self.data["dt"] * 1e6, 0])

        # the first time the amplitude image is loaded, update colormap to cut off values below 10th percentile
        self.im_data.set_clim([self.mindB_data, 0.0])
        self.im_clut.set_clim([self.mindB_clut, 0.0])

        # set slider bounds
        self.s_cmin.valmin = self.mindB_data - 10
        self.s_cmin.valmax = self.mindB_data + 10
        self.s_cmin.valinit = self.mindB_data
        self.s_cmax.valmin = -10
        self.s_cmax.valmax = 10
        self.s_cmax.valinit = 0

        self.update_slider()

        # set clutter sim visibility to false
        self.im_clut.set_visible(False)

        # label axes    
        self.ax.set(xlabel = "along-track distance [km]", ylabel = "two-way travel time [microsec.]")

        # update the canvas
        self.dataCanvas._tkcanvas.pack()
        self.dataCanvas.draw()

        # save background
        self.axbg = self.dataCanvas.copy_from_bbox(self.ax.bbox)


    # get_pickState is a method to return the current picking state
    def get_pickState(self):
        return self.pick_state


    # set_pickState is a method to generate a new pick dictionary layer and plot the data
    def set_pickState(self, state):
        self.pick_state = state
        if self.pick_state == True:
            # if previous layers already exist, call pick interp and clear points for new layer
            if len(self.xln) >= 2:
                self.pick_layer += 1
            # initialize pick index and twtt dictionaries for current picking layer
            self.pick_dict["layer_" + str(self.pick_layer)] = np.ones(self.data["num_trace"])*-1
            self.pickLabel.config(text="Picking Layer:\t" + str(self.pick_layer), fg="#008000")          

        elif self.pick_state == False:
            if len(self.xln) >=  2:
                self.pick_layer += 1
                # only advance pick layer if picks made on previous layer
            self.pickLabel.config(fg="#FF0000")
        self.plot_picks()


    # addseg is a method to for user to generate picks
    def addseg(self, event):
        if self.f_loadName:
            if (event.inaxes != self.ax):
                return
            # find nearest index to event.xdata
            self.pick_idx_1 = utils.find_nearest(self.data["dist"], event.xdata)
            # check if picking state is a go
            if self.pick_state == True:
                self.xln.append(event.xdata)
                self.yln.append(event.ydata)

                # redraw pick quickly with blitting
                self.pick.set_data(self.xln, self.yln)
                self.dataCanvas.restore_region(self.axbg)
                self.ax.draw_artist(self.pick)
                self.ax.draw_artist(self.saved_pick)
                self.dataCanvas.blit(self.ax.bbox)
                # self.fig.canvas.draw()


                # if more than two picks, call pick_interp
                if len(self.xln) >= 2:
                    self.pick_interp()
            # plot pick location to basemap
            if self.basemap and self.basemap.get_state() == 1:
                self.basemap.plot_idx(self.pick_idx_1)


    # pick_interp is a method for linearly interpolating twtt between pick locations
    def pick_interp(self):
        # if there are at least two picked points, find range of all trace numbers within their range
        try:
            pick_idx_0 = utils.find_nearest(self.data["dist"], self.xln[-2])
            self.pick_dict["layer_" + str(self.pick_layer)][pick_idx_0] = self.yln[-2]
            self.pick_dict["layer_" + str(self.pick_layer)][self.pick_idx_1] = self.yln[-1]
            pick_idx = np.arange(pick_idx_0,self.pick_idx_1 + 1)
            # linearly interpolate twtt values between pick points at idx_0 and idx_1
            self.pick_dict["layer_" + str(self.pick_layer)][pick_idx] = np.interp(pick_idx, [pick_idx_0,self.pick_idx_1], [self.yln[-2],self.yln[-1]])

            self.xln_old.extend(self.data["dist"][pick_idx])
            self.yln_old.extend(self.pick_dict["layer_" + str(self.pick_layer)][pick_idx])
            self.pick.set_data(self.xln, self.yln) 

        except Exception as err:
            print(err)
    

    # plot_picks is a method to plot the existing pick layers
    def plot_picks(self):
        # remove saved picks
        del self.xln[:]
        del self.yln[:]  
        self.pick.set_data(self.xln, self.yln)
        self.saved_pick.set_offsets(np.c_[self.xln_old,self.yln_old])
        self.dataCanvas.restore_region(self.axbg)
        self.ax.draw_artist(self.pick)
        self.ax.draw_artist(self.saved_pick)
        self.dataCanvas.blit(self.ax.bbox)
        # self.fig.canvas.draw()

    def onkey(self, event):
        # on-key commands
        if event.key =="c":
            # clear the drawing of line segments
            self.clear_picks()
        elif event.key =="delete":
            # remove last segment
            self.clear_last()
        elif event.key==" ":
            self.set_im()


    def clear_picks(self):
        # clear all picks
        if len(self.xln + self.xln_old) > 0 and tk.messagebox.askokcancel("Warning", "Clear all picks?", icon = "warning") == True:
            del self.xln[:]
            del self.yln[:]
            del self.yln_old[:]
            del self.xln_old[:]
            self.pick.set_data(self.xln, self.yln)
            self.saved_pick.set_offsets(np.c_[self.xln_old,self.yln_old])
            self.pickLabel.config(text="Picking Layer:\t0")
            self.pick_layer = 0
            self.fig.canvas.draw()


    def clear_last(self):
        # clear last pick
        if len(self.xln) > 0:
            del self.xln[-1:]
            del self.yln[-1:]
            self.pick.set_data(self.xln, self.yln)
            self.fig.canvas.draw()


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
        self.s_cmax.valmin = -10
        self.s_cmax.valmax = 10
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
            self.s_cmax.valinit = 0
        else: 
            # if clutter has been shown before revert to previous colorbar values
            self.im_clut.set_clim([self.clut_cmin, self.clut_cmax])
            self.s_cmin.valinit = self.clut_cmin
            self.s_cmax.valinit = self.clut_cmax

        self.s_cmin.valmin = self.mindB_clut - 10
        self.s_cmin.valmax = self.mindB_clut + 10            
        self.s_cmax.valmin = -10
        self.s_cmax.valmax = 10
        self.update_slider()
        # reverse visilibilty
        self.im_data.set_visible(False)
        self.im_clut.set_visible(True)
        # set flag to indicate that clutter has been viewed for resetting colorbar limits
        self.clut_imSwitch_flag = True    
        # redraw canvas
        self.fig.canvas.draw()
        self.im_status.set("clut")

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
            self.s_cmax.valmin = -10
            self.s_cmax.valmax = 10
            self.s_cmax.valinit = 0
        else:
            # if clutter is displayed, change slider bounds
            self.s_cmin.valmin = self.mindB_clut - 10
            self.s_cmin.valmax = self.mindB_clut + 10
            self.s_cmin.valinit = self.mindB_clut
            self.s_cmax.valmin = -10
            self.s_cmax.valmax = 10
            self.s_cmax.valinit = 0
        self.update_slider()
        self.cmap_update()



    # exit_warningn is a method which closes the window if no picks exist, or if the user would like to discard existing picks
    def exit_warning(self):
        # check if picks have been made and saved
        if len(self.xln + self.xln_old) > 0 and self.f_saveName == "":
            if tk.messagebox.askokcancel("Warning", "Exit NOSEpick without saving picks?", icon = "warning") == True:
                self.parent.destroy()
        else:
            self.parent.destroy()


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
        self.set_vars()


    # get_pickLen is a method to return the length of existing picks
    def get_pickLen(self):
        return len(self.xln + self.xln_old)
        

    # get_nav method returns the nav data       
    def get_nav(self):
        return self.data["navdat"]


    # get_idx is a method that reurns the trace index of a click event on the image
    def get_idx(self):
        return self.pick_idx_1


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