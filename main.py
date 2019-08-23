"""
NOSEpick - currently in development stages
created by: Brandon S. Tober and Michael S. Christoffersen
date: 25JUN19

last updated: 223AUG19

environment requirements in nose_env.yml
"""

### IMPORTS ###
import ingester
import os, sys, scipy
import numpy as np
import matplotlib as mpl
mpl.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
import tkinter as tk
from tkinter import Button, Frame, messagebox, Canvas, filedialog
# from PIL import ImageTk

### USER SPECIFIED VARS ###
in_path = "/mnt/Swaps/MARS/targ/supl/UAF/2018/aug/export/"
map_path = "/mnt/Swaps/MARS/targ/supl/grid-AKDEM/"


### CODE ###
name = in_path.split("/")[-1].rstrip(".mat")
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
        self.switchIm = Frame(self.master)
        self.switchIm.pack(side="bottom")
        self.display = Frame(self.master)
        self.display.pack(side="bottom", fill="both", expand=1)
        # blank data canvas
        self.fig = mpl.figure.Figure()          # need to make two of these - add seg canvas on top of image canvas!!!!
        self.ax = self.fig.add_subplot(111)
        self.dataCanvas = FigureCanvasTkAgg(self.fig, self.master)
        # self.dataCanvas.get_tk_widget().pack(in_=self.display, side="bottom", fill="both", expand=1)
        # self.dataCanvas.draw()
        # button for help message
        self.instButton = Button(self.master, text = "Instructions", command = self.inMsg)
        self.instButton.pack(in_=self.controls, side="left")
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
        # button for exit
        self.exitButton = Button(text = "Exit", fg = "red", command = self.close_window)
        self.exitButton.pack(in_=self.controls, side="left")
        # button to toggle on radargram
        self.radarButton = Button(text = "radar", command = self.show_radar)
        self.radarButton.pack(in_=self.switchIm, side="left")        
        # button to toggle on clutter
        self.clutterButton = Button(text = "clutter", command = self.show_clutter)
        self.clutterButton.pack(in_=self.switchIm, side="left")        
        # call information messagebox
        self.inMsg()
        # empty fields for pick
        self.xln = []
        self.yln = []
        self.pick, = self.ax.plot([],[],"r")  # empty line
        # register click and key events
        self.key = self.fig.canvas.mpl_connect("key_press_event", self.onkey)
        self.click = self.fig.canvas.mpl_connect("button_press_event", self.addseg)
        # variable declarations
        self.toolbar = None
        self.f_loadName = ""
        self.map_loadName = ""
        self.f_saveName = ""

    def inMsg(self):
        # instructions button message box
        messagebox.showinfo("NOSEpick Instructions",
        """Nearly Optimal Subsurface Extractor:
        \n\n1. Load button to open radargram
        \n2. Click along reflector surface to pick
        \n\t\u2022<backspace> to remove the last
        \n\t\u2022<c> to remove all
        \n3. Radar and clutter buttons to toggle
        \n4. Save button to export picks
        \n5. Next button to load next file
        \n6. Exit button to close application""")

    def load(self):
        # bring up dialog box for user to load data file
        self.igst = ingester.ingester("h5py")
        self.f_loadName = filedialog.askopenfilename(initialdir = in_path,title = "Select file",filetypes = (("mat files","*.mat"),("all files","*.*")))
        if self.f_loadName:
            print("Loading: ", self.f_loadName)
            self.data = self.igst.read(self.f_loadName)
            self.dtype = "amp"
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
            self.toolbar.destroy() 
        self.dataCanvas.get_tk_widget().pack(in_=self.display, side="bottom", fill="both", expand=1)
        self.ax.imshow(np.log(np.power(self.data[self.dtype],2)), cmap="gray", aspect="auto", extent=[self.data["dist"][0], self.data["dist"][-1], self.data["amp"].shape[0] * self.data["dt"] * 1e6, 0])
        self.ax.set_title(name)
        self.ax.set(xlabel = "along-track distance [km]", ylabel = "two-way travel time [microsec.]")
        # add matplotlib figure nav toolbar
        self.toolbar = NavigationToolbar2Tk(self.dataCanvas, self.master)
        self.toolbar.update()
        self.dataCanvas._tkcanvas.pack()
        self.dataCanvas.draw()

    def basemap(self):
        # pull track up on dem basemap
        # if self.f_loadName:
        self.map_loadName = filedialog.askopenfilename(initialdir = map_path,title = "Select file",filetypes = (("tif files","*.tif"),("all files","*.*")))
        if self.map_loadName:
            print("Loading Basemap: ", self.map_loadName)
            self.basemap_window = tk.Toplevel(self.master)
            self.basemap_window.title("NOSEpick - Map Window")
            self.map_display = Frame(self.basemap_window)
            self.map_display.pack(side="bottom", fill="both", expand=1)
            self.mapFig = mpl.figure.Figure()
            self.map_ax = self.mapFig.add_subplot(111)
            self.map_dataCanvas = FigureCanvasTkAgg(self.mapFig, self.master)
            self.map_dataCanvas.get_tk_widget().pack(in_=self.map_display, side="bottom", fill="both", expand=1)


    def addseg(self, event):
        # add line segments with user input
        if (event.inaxes != self.ax):
            return
        # print("[" + event.xdata.astype(str) + ", " + event.ydata.astype(str) + "]")
        self.xln.append(event.xdata)
        self.yln.append(event.ydata)
        self.pick.set_data(self.xln, self.yln)
        self.fig.canvas.draw()

    def onkey(self, event):
        # on-key commands
        if event.key =="c":
            # clear the drawing of line segments
            if messagebox.askokcancel("Warning", "Clear all picks?", icon = "warning") == True:
                self.clear_picks()
        elif event.key =="backspace":
            # remove last segment
            self.clear_last()
        elif event.key =="escape":
            self.close_window()
    
    def savePick(self):
        # save picks
        if len(self.xln) > 0 and len(self.yln) > 0:
            self.f_saveName = filedialog.asksaveasfilename(initialdir = "./",title = "Save As",filetypes = (("comma-separated values","*.csv"),))
            if self.f_saveName:
                print("Exporting picks: ", self.f_saveName)
                self.x_pickList = []
                self.y_pickList = []
                for _i in range(len(self.xln)):
                    self.x_pickList.append(self.xln[_i])
                    self.y_pickList.append(self.yln[_i])
                self.pickArray = np.column_stack((np.asarray(self.x_pickList), np.asarray(self.y_pickList)))
                np.savetxt(self.f_saveName, self.pickArray, delimiter=",", newline = "\n", fmt="%.8f")

    def clear_picks(self):
        # clear all picks
        if len(self.xln) and len(self.yln) > 0:
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
                    self.matplotCanvas()
                else:
                    print("Note: " + self.f_loadName.split("/")[-1] + " is the last file in " + self.file_path)

    def show_radar(self):
        # toggle to radar data
        if self.dtype == "clutter":
            self.dtype = "amp"
            self.matplotCanvas()

    def show_clutter(self):
        # toggle to clutter sim
        if self.dtype == "amp":
            self.dtype = "clutter"
            self.matplotCanvas()

    def close_window(self):
        # destroy canvas
        # first check if picks have been made and saved
        if len(self.xln) > 0 and len(self.yln) > 0 and self.f_saveName == "":
            if messagebox.askokcancel("Warning", "Exit NOSEpick without saving picks?", icon = "warning") == True:
                self.master.destroy()
        else:
            self.master.destroy()

    def save_warning(self):
        # warning to save picks before loading next file
        # first check if picks have been made and saved
        if len(self.xln) > 0 and len(self.yln) > 0 and self.f_saveName == "":
            if messagebox.askokcancel("Warning", "Load next track without saving picks?", icon = "warning") == True:
                # clear picks
                self.clear_picks()
                return True
        else: 
            return True



### INITIALIZE ###
root = tk.Tk()
# get screen size - open root window half screen
w, h = root.winfo_screenwidth(), root.winfo_screenheight()
root.geometry("%dx%d+0+0" % (.5*w, .5*h))
# call the NOSEpickGUI class
gui = NOSEpickGUI(root)
root.mainloop()