"""
NOSEpick - currently in development stages
created by: Brandon S. Tober and Michael S. Christoffersen
date: 25JUN19
last updated: 19SEP2019
environment requirements in nose_env.yml
"""

### IMPORTS ###
# import ingester
import utils
import imPick
import basemap
from tools import *
import os, sys, scipy
import numpy as np
import matplotlib as mpl
mpl.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import tkinter as tk
from tkinter import Button, Frame, messagebox, Canvas, filedialog, Menu, Radiobutton

# MainGUI is the NOSEpick class which sets the gui interface and holds operating variables
class MainGUI(tk.Tk):
    def __init__(self, master, in_path, map_path):
        self.master = master
        self.in_path = in_path
        self.map_path = map_path

    # setup is a method which generates the app menubar and buttons and initializes some vars
    def setup(self):
        self.f_loadName = ""
        self.f_saveName = ""
        self.map_loadName = ""
        self.im_status = tk.StringVar()
        self.im_status.set("data")       

        # generate menubar
        menubar = Menu(self.master)

        # create individual menubar items
        fileMenu = Menu(menubar, tearoff=0)
        pickMenu = Menu(menubar, tearoff=0)
        viewMenu = Menu(menubar, tearoff=0)
        mapMenu = Menu(menubar, tearoff=0)
        helpMenu = Menu(menubar, tearoff=0)

        # file menu items
        fileMenu.add_command(label="Open    [Ctrl+O]", command=self.open_loc)
        fileMenu.add_command(label="Save    [Ctrl+S]", command=self.save_loc)
        fileMenu.add_command(label="Next         [>]", command=self.next_loc)
        fileMenu.add_command(label="Exit    [Ctrl+Q]", command=self.close_window)

        # pick menu items
        pickMenu.add_command(label="Begin/New Layer    [Ctrl+N]", command=self.new_pick)
        pickMenu.add_command(label="Stop               [Q]", command=self.stop_pick)
        pickMenu.add_separator()
        pickMenu.add_command(label="Optimize")

        # view menu items
        viewMenu.add_radiobutton(label="Radargram", variable=self.im_status, value="data",command=self.im_switch)
        viewMenu.add_radiobutton(label="Cluttergram", variable=self.im_status, value="clut",command=self.im_switch)
        viewMenu.add_separator()
        viewMenu.add_command(label="Trace-View")

        # map menu items
        mapMenu.add_command(label="Open    [Ctrl+M]", command=self.map_loc)

        # help menu items
        helpMenu.add_command(label="Instructions", command=self.help)

        # add items to menubar
        menubar.add_cascade(label="File", menu=fileMenu)
        menubar.add_cascade(label="Pick", menu=pickMenu)
        menubar.add_cascade(label="View", menu=viewMenu)
        menubar.add_cascade(label="Map", menu=mapMenu)
        menubar.add_cascade(label="Help", menu=helpMenu)
        
        # add the menubar to the window
        self.master.config(menu=menubar)

        # build data display frame
        self.display = tk.Frame(self.master)
        self.display.pack(side="bottom", fill="both", expand=1)

        # initialize imPick
        self.imPick = imPick.imPick(self.master, self.display)
        self.imPick.set_vars()
        
        # add radio buttons for toggling between radargram and clutter-sim
        radarRad = Radiobutton(self.master, text="Radargram", variable=self.im_status, value="data",command=self.im_switch).pack(side="left")
        clutterRad = Radiobutton(self.master,text="Cluttergram", variable=self.im_status, value="clut",command=self.im_switch).pack(side="left")  
        
        # bind keypress events
        self.master.bind("<Key>", self.key)

        self.open_loc()


    # key is a method to handle UI keypress events
    def key(self,event):
        # event.state & 4 True for Ctrl+Key
        # event.state & 1 True for Shift+Key
        # Ctrl+O open file
        if event.state & 4 and event.keysym == "o":
            self.open_loc()

        # Ctrl+S save picks
        elif event.state & 4 and event.keysym == "s":
            self.save_loc()

        # Ctrl+M open map
        elif event.state & 4 and event.keysym == "m":
            self.map_loc()

        # Ctrl+N begin pick
        elif event.state & 4 and event.keysym == "n":
            self.new_pick()

        # Ctrl+Q new pick layer
        elif event.state & 4 and event.keysym == "q":
            self.close_window()

        # shift+. (>) next file
        elif event.state & 1 and event.keysym == "greater":
            self.next_loc()

        # tab key to toggle between radar and clutter sim display
        elif event.keysym == "Tab":
            self.im_switch()

        # Escape key to stop picking current layer
        elif event.keysym == "Escape":
            self.stop_pick()


    # im_switch is a method to toggle imPick between data and clutter images
    def im_switch(self):
        if self.f_loadName:
            if self.im_status.get() == "data":
                self.im_status.set("clut")
                self.imPick.set_im(self.im_status.get())

            elif self.im_status.get() == "clut":
                self.im_status.set("data")
                self.imPick.set_im(self.im_status.get())


    # close_window is a gui method to call the imPick close_warning
    def close_window(self):
        self.imPick.exit_warning()


    # open_loc is a gui method which has the user select and input data file - then passed to imPick.load()
    def open_loc(self):
        self.f_loadName = filedialog.askopenfilename(initialdir = self.in_path,title = "Select file",filetypes = (("mat files","*.mat"),("all files","*.*")))
        if self.f_loadName:
            self.imPick.load(self.f_loadName)
            self.im_status.set("data")

        if self.map_loadName:
            # pass basemap to imPick for plotting pick location
            self.basemap.set_nav(self.imPick.get_nav())
            self.imPick.get_basemap(self.basemap)            


    # save_loc is method to receieve the desired pick save location from user input
    def save_loc(self):
        if self.f_loadName and self.imPick.get_pickLen() > 0:
            self.f_saveName = filedialog.asksaveasfilename(initialdir = self.in_path,title = "Save As",filetypes = (("comma-separated values","*.csv"),))
    

    # map_loc is a method to get the desired basemap location and initialize
    def map_loc(self):
        self.map_loadName = filedialog.askopenfilename(initialdir = self.map_path, title = "Select file", filetypes = (("GeoTIFF files","*.tif"),("all files","*.*")))
            
        if self.map_loadName:
            self.basemap = basemap.basemap(self.master, self.map_loadName)
            self.basemap.map()

        if self.f_loadName:
            # pass basemap to imPick for plotting pick location
            self.basemap.set_nav(self.imPick.get_nav())
            self.imPick.get_basemap(self.basemap)


    # new_pick is a method which begins a new imPick pick layer
    def new_pick(self):
        if self.f_loadName:
            self.imPick.set_pickState(True)


    # stop_pick is a method which terminates the current imPick pick layer
    def stop_pick(self):
        if self.imPick.get_pickState() is True:
            self.imPick.set_pickState(False)


    # next_loc is a method to get the filename of the next data file in the directory then call imPick.load()
    def next_loc(self):
        if self.f_loadName and self.imPick.nextSave_warning() == True:
            # get index of crurrently displayed file in directory
            file_path = self.f_loadName.rstrip(self.f_loadName.split("/")[-1])
            file_list = os.listdir(file_path)
            file_list.sort()
            for _i in range(len(file_list)):
                if file_list[_i] == self.f_loadName.split("/")[-1]:
                    file_index = _i
            # add one to index to load next file
            file_index += 1

            # check if more files exist in directory following current file
            if file_index <= (len(file_list) - 1):
                self.f_loadName = (file_path + file_list[file_index])
                self.imPick.clear_canvas()
                self.imPick.load(self.f_loadName)

            else:
                print("Note: " + self.f_loadName.split("/")[-1] + " is the last file in " + file_path)


    def help(self):
        # help message box
        messagebox.showinfo("NOSEpick Instructions",
        """Nearly Optimal Subsurface Extractor:
        \n\n1. Load button to open radargram
        \n2. Click along reflector surface to pick
        \n\t\u2022<backspace> to remove the last
        \n\t\u2022<c> to remove all
        \n3. Radar and clutter buttons to toggle
        \n4. Next button to load next file
        \n5. Save button to export picks
        \n6. Map button to display basemap
        \n7. Exit button to close application""")