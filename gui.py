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
import os, sys, scipy
import numpy as np
import matplotlib as mpl
mpl.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import tkinter as tk

# MainGUI is the NOSEpick class which sets the gui interface and holds operating variables
class MainGUI(tk.Frame):
    def __init__(self, parent, in_path, out_path, map_path, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)
        self.parent = parent
        self.in_path = in_path
        self.out_path = out_path
        self.map_path = map_path
        self.setup()


    # setup is a method which generates the app menubar and buttons and initializes some vars
    def setup(self):
        self.f_loadName = ""
        self.f_saveName = ""
        self.map_loadName = "" 

        # generate menubar
        menubar = tk.Menu(self.parent)

        # create individual menubar items
        fileMenu = tk.Menu(menubar, tearoff=0)
        pickMenu = tk.Menu(menubar, tearoff=0)
        viewMenu = tk.Menu(menubar, tearoff=0)
        mapMenu = tk.Menu(menubar, tearoff=0)
        helpMenu = tk.Menu(menubar, tearoff=0)

        # file menu items
        fileMenu.add_command(label="Open    [Ctrl+O]", command=self.open_loc)
        fileMenu.add_command(label="Save    [Ctrl+S]", command=self.save_loc)
        fileMenu.add_command(label="Next     [Right]", command=self.next_loc)
        fileMenu.add_command(label="Exit    [Ctrl+Q]", command=self.close_window)

        # pick menu items
        pickMenu.add_command(label="New     [Ctrl+N]", command=self.new_pick)
        pickMenu.add_command(label="Stop    [Escape]", command=self.stop_pick)
        pickMenu.add_separator()
        pickMenu.add_command(label="Optimize")

        # view menu items
        viewMenu.add_command(label="Trace-View")

        # map menu items
        mapMenu.add_command(label="Open     [Ctrl+M]", command=self.map_loc)

        # help menu items
        helpMenu.add_command(label="Instructions", command=self.help)
        helpMenu.add_command(label="Keyboard Shortcuts", command=self.shortcuts)

        # add items to menubar
        menubar.add_cascade(label="File", menu=fileMenu)
        menubar.add_cascade(label="Pick", menu=pickMenu)
        menubar.add_cascade(label="View", menu=viewMenu)
        menubar.add_cascade(label="Map", menu=mapMenu)
        menubar.add_cascade(label="Help", menu=helpMenu)
        
        # add the menubar to the window
        self.parent.config(menu=menubar)

        # initialize imPick
        self.imPick = imPick.imPick(self.parent)

        # bind keypress events
        self.parent.bind("<Key>", self.key)

        # handle x-button closing of window
        self.parent.protocol("WM_DELETE_WINDOW", self.close_window)

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

        # Ctrl+Q close NOSEpick
        elif event.state & 4 and event.keysym == "q":
            self.close_window()

        # shift+. (>) next file
        elif event.keysym =="Right":
            self.next_loc()

        # Escape key to stop picking current layer
        elif event.keysym == "Escape":
            self.stop_pick()


    # close_window is a gui method to call the imPick close_warning
    def close_window(self):
        self.imPick.exit_warning()


    # open_loc is a gui method which has the user select and input data file - then passed to imPick.load()
    def open_loc(self):
        # if previous track has already been opened, clear imPick canvas
        if self.f_loadName:
            self.imPick.clear_canvas()                

        self.imPick.set_vars()
        
        # select input file
        self.f_loadName = tk.filedialog.askopenfilename(initialdir = self.in_path,title = "Select file",filetypes = (("data files", ".mat .h5"),("all files",".*")))
        # if input selected, pass filename to imPick.load()
        if self.f_loadName:
            self.imPick.load(self.f_loadName)

        # pass basemap to imPick for plotting pick location
        if self.map_loadName:
            self.basemap.clear_nav()
            self.basemap.set_nav(self.imPick.get_nav())
            self.imPick.get_basemap(self.basemap)            


    # save_loc is method to receieve the desired pick save location from user input
    def save_loc(self):
        if self.f_loadName and self.imPick.get_pickLen() > 0:
            self.f_saveName = tk.filedialog.asksaveasfilename(initialfile = os.path.splitext(self.f_loadName.split("/")[-1])[0] + "_pk",
                                initialdir = self.out_path,title = "Save As",filetypes = (("comma-separated values","*.csv"),))
        if self.f_saveName:
            self.imPick.save(self.f_saveName)
    

    # map_loc is a method to get the desired basemap location and initialize
    def map_loc(self):
        self.map_loadName = tk.filedialog.askopenfilename(initialdir = self.map_path, title = "Select file", filetypes = (("GeoTIFF files","*.tif"),("all files","*.*")))
            
        if self.map_loadName:
            self.basemap = basemap.basemap(self.parent, self.map_loadName)
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


                if self.map_loadName and self.basemap.get_state() == 1:
                    self.basemap.clear_nav()
                    self.basemap.set_nav(self.imPick.get_nav())
                    self.imPick.get_basemap(self.basemap)

            else:
                print("Note: " + self.f_loadName.split("/")[-1] + " is the last file in " + file_path)


    def help(self):
        # help message box
        tk.messagebox.showinfo("Instructions",
        """Nearly Optimal Subsurface Extractor:
        \n\n1. File->Load to load data file
        \n2. Map->Open to load basemap
        \n3. Pick->New to begin new pick layer 
        \n4. Click along reflector surface to pick\n   horizon
        \n\t\u2022[backspace] to remove the last
        \n\t\u2022[c] to remove all
        \n5. Pick->Stop to end current pick layer
        \n6. Radio buttons to toggle between radar\n   and clutter images
        \n7. File->Save to export picks
        \n8. File->Next to load next data file
        \n9. File->Quit to exit application""")


    def shortcuts(self):
        # shortcut list
        tk.messagebox.showinfo("Keyboard Shortcuts",
        """[Ctrl+o]\tOpen radar data file
        \n[Ctrl+m]\tOpen basemap window
        \n[Ctrl+n]\tBegin new pick layer
        \n[Escape]\tEnd current pick layer
        \n[Spacebar]\tToggle between radar and\t\t\tclutter images
        \n[Ctrl+s]\tExport pick data
        \n[Right]\t\tOpen next file in \t\t\t\tdirectory
        \n[Ctrl+q]\tQuit NOSEpick""")