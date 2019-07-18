"""
NOSEpick - currently in development stages
created by: Brandon S. Tober and Michael S. Christoffersen
date: 25JUN19

dependencies in requirements.txt
"""

### IMPORTS ###
import ingester
import sys, scipy
import numpy as np
import matplotlib as mpl
mpl.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
import tkinter as tk
from tkinter import Button, Frame, messagebox, Canvas, filedialog

### USER SPECIFIED VARS ###
in_path = "/mnt/Swaps/MARS/targ/supl/UAF/"


### CODE ###
name = in_path.split("/")[-1].rstrip(".mat")

class NOSEpickGUI(tk.Tk):
    def __init__(self, master):
        self.master = master
        master.title("NOSEpick")
        self.setup()

    def setup(self):
        # frames for data display and UI
        self.controls = Frame(self.master)
        self.controls.pack(side="top")
        self.swithIm = Frame(self.master)
        self.swithIm.pack(side="bottom")
        self.display = Frame(self.master)
        self.display.pack(side="bottom", fill="both", expand=1)
        # blank data canvas
        self.fig = mpl.figure.Figure()
        self.ax = self.fig.add_subplot(111)
        self.dataCanvas = FigureCanvasTkAgg(self.fig, self.master)
        # self.dataCanvas.get_tk_widget().pack(in_=self.display, side="bottom", fill="both", expand=1)
        # self.dataCanvas.draw()
        # button for help message
        self.instButton = Button(self.master, text = "Instructions", command = self.insMsg)
        self.instButton.pack(in_=self.controls, side="left")
        # button for loading data
        self.loadButton = Button(self.master, text = "Load", command = self.load)
        self.loadButton.pack(in_=self.controls, side="left")
        # button for saving
        self.exitButton = Button(text = "Save", command = self.savePick)
        self.exitButton.pack(in_=self.controls, side="left")
        # button for exit
        self.exitButton = Button(text = "Exit", fg = "red", command = self.close_window)
        self.exitButton.pack(in_=self.controls, side="left")
        # button to toggle on radargram
        self.radarButton = Button(text = "radar", command = self.show_radar)
        self.radarButton.pack(in_=self.swithIm, side="left")        
        # button to toggle on clutter
        self.clutterButton = Button(text = "clutter", command = self.show_clutter)
        self.clutterButton.pack(in_=self.swithIm, side="left")        
        # call information messagebox
        self.insMsg()
        # empty fields for pick
        self.xln = []
        self.yln = []
        self.pick, = self.ax.plot([],[],"r")  # empty line
        # register click and key events
        self.keye = self.fig.canvas.mpl_connect("key_press_event", self.onkey)
        self.clicke = self.fig.canvas.mpl_connect("button_press_event", self.addseg)

    def load(self):
        # can be made fancier in the future
        igst = ingester.ingester("h5py")
        self.f_loadName = filedialog.askopenfilename(initialdir = in_path,title = "Select file",filetypes = (("mat files","*.mat"),("all files","*.*")))
        if self.f_loadName:
            print("Loading: ", self.f_loadName)
            self.data = igst.read(self.f_loadName)
            self.matplotCanvas()

    def matplotCanvas(self):
        # create matplotlib figure and use imshow to display radargram
        self.dataCanvas.get_tk_widget().pack(in_=self.display, side="bottom", fill="both", expand=1)
        self.ax.imshow(np.log(np.power(self.data["amp"],2)), cmap="gray", aspect="auto", extent=[self.data["dist"][0], self.data["dist"][-1], self.data["amp"].shape[0] * self.data["dt"] * 1e6, 0])
        # self.ax.imshow(np.log(self.data["clutter"]), cmap="gray", aspect="auto", extent=[self.data["dist"][0], self.data["dist"][-1], self.data["amp"].shape[0] * self.data["dt"] * 1e6, 0])
        self.ax.set_title(name)
        self.ax.set(xlabel = "along-track distance [km]", ylabel = "two-way travel time [microsec.]")
        # add matplotlib figure nav toolbar
        toolbar = NavigationToolbar2Tk(self.dataCanvas, self.master)
        toolbar.update()
        self.dataCanvas._tkcanvas.pack()
        self.dataCanvas.draw()

    def addseg(self, event):
        # add line segments with user input
        if (event.inaxes != self.ax):
            return
        self.xln.append(event.xdata)
        self.yln.append(event.ydata)
        self.pick.set_data(self.xln, self.yln)
        self.fig.canvas.draw()

    def onkey(self, event):
        # on-key commands
        if event.key =="c":
            # clear the drawing of line segments
            if messagebox.askokcancel("Warning", "Clear all picks?", icon = "warning") == True:
                if len(self.xln) and len(self.yln) > 0:
                    del self.xln[:]
                    del self.yln[:]
                    self.pick.set_data(self.xln, self.yln)
                    self.fig.canvas.draw()
    
        elif event.key =="backspace":
            # remove last segment
            if len(self.xln) and len(self.yln) > 0:
                del self.xln[-1:]
                del self.yln[-1:]
                self.pick.set_data(self.xln, self.yln)
                self.fig.canvas.draw()
    
    def insMsg(self):
        # instructions button message box
        messagebox.showinfo("NOSEpick Instructions",
        """Nearly Optimal Subsurface Extractor:
        \n\n1. Load button to open radargram
        \n2. Click along reflector surface to pick
        \n\t\u2022<backspace> to remove the last
        \n\t\u2022<c> to remove all
        \n3. Radar and clutter buttons to toggle
        \n4. Save button to export picks
        \n5. Exit button to close application""")

    def savePick(self):
        # save picks
        self.f_saveName = filedialog.asksaveasfilename(initialdir = "./",title = "Save As",filetypes = (("comma-separated values","*.csv"),))
        if self.f_saveName:
            print("Exporting picks: ", self.f_saveName)
            self.x_pickList = []
            self.y_pickList = []
            for _i in range(len(self.xln)):
                self.x_pickList.append(self.xln[_i])
                self.y_pickList.append(self.yln[_i])
            self.pickArray = np.column_stack(np.asarray(self.x_pickList), np.asarray(self.y_pickList))
            np.savetxt(self.f_saveName, self.pickArray, delimiter=",", newline = '\n', fmt="%.8f")

    def show_radar(self):
        # toggle to radar data
        return

    def show_clutter(self):
        # toggle to clutter sim
        return

    def close_window(self):
        # destroy canvas upon Exit button click
        if messagebox.askokcancel("Warning", "Exit NOSEpick?", icon = "warning") == True:
            self.master.destroy()

# initialize the tkinter window
root = tk.Tk()
# get screen size - open root window half screen
w, h = root.winfo_screenwidth(), root.winfo_screenheight()
root.geometry("%dx%d+0+0" % (.5*w, .5*h))
# call the NOSEpickGUI class
gui = NOSEpickGUI(root)
root.mainloop()