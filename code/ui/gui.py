"""
NOSEpick - Nearly Optimal Subsurface Extractor
created by: Brandon S. Tober and Michael S. Christoffersen
date: 25JUN19
last updated: 05FEB20
environment requirements in nose_env.yml
"""
### imports ###
from ui import impick, wvpick, basemap 
from tools import utils
from radar import processing
from ingest import ingest
import os, sys, scipy, glob, configparser
import numpy as np
import matplotlib as mpl
mpl.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import tkinter as tk
import tkinter.ttk as ttk

# mainGUI is the NOSEpick class which sets the graphical user interface and holds operating variables to pass between packages
class mainGUI(tk.Frame):
    def __init__(self, parent, datPath, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)
        self.parent = parent
        # read and parse config
        self.conf = configparser.ConfigParser()
        self.conf.read("config.ini")
        if datPath:
            self.datPath = datPath
        else:
            self.datPath = self.conf["paths"]["datPath"]
        self.eps_r = tk.DoubleVar(value=self.conf["params"]["eps_r"])
        self.os = sys.platform
        self.setup()


    # setup is a method which generates the app menubar and buttons and initializes some vars
    def setup(self):
        self.f_loadName = ""
        self.f_saveName = ""
        self.map_loadName = ""

        self.userName = tk.StringVar(value="")
        self.figSize = tk.StringVar(value="21,7")
        self.cmap = tk.StringVar(value="Greys_r")
        self.debugState = tk.BooleanVar()
        self.debugState.set(False)

        # menubar structure     
        # |-file
        # |  |-open
        # |  |-load picks
        # |  |-next
        # |  |-save
        # |  |-settings
        # |  |  |-preferences
        # |  |  |-set working directory
        # |  |  |-set output directory
        # |  |-exit
        # |-pick
        # |  |-surface
        # |  |  |-new
        # |  |  |-end
        # |  |  |-clear
        # |  |-subsurface
        # |  |  |-new
        # |  |  |-end
        # |  |  |-clear
        # |  |  |-clear file
        # |-map
        # |  |-open
        # |-processing
        # |  |-dewow
        # |  |-remove mean trace
        # |  |-filter
        # |  |  |-low pass
        # |  |-gain
        # |  |  |-acg
        # |-help
        # |  |-instructions
        # |  |-keyboard shortcuts

        # generate menubar
        menubar = tk.Menu(self.parent)

        # create individual menubar items
        fileMenu = tk.Menu(menubar, tearoff=0)
        pickMenu = tk.Menu(menubar, tearoff=0)
        mapMenu = tk.Menu(menubar, tearoff=0)
        procMenu = tk.Menu(menubar, tearoff=0)
        helpMenu = tk.Menu(menubar, tearoff=0)

        # file menu items
        fileMenu.add_command(label="open       [ctrl+o]", command=self.open_data)
        fileMenu.add_command(label="load picks", command=self.load_picks)
        fileMenu.add_command(label="next        [right]", command=self.next_loc)
        fileMenu.add_command(label="save       [ctrl+s]", command=self.save_loc)


        # settings submenu
        settingsMenu = tk.Menu(fileMenu,tearoff=0)
        settingsMenu.add_command(label="preferences", command=self.settings)
        settingsMenu.add_command(label="set working directory", command=self.set_home)
        settingsMenu.add_command(label="set output directory", command=self.set_out)

        fileMenu.add_cascade(label="settings", menu = settingsMenu)

        fileMenu.add_command(label="exit       [ctrl+q]", command=self.close_window)

        # pick menu subitems
        surfacePickMenu = tk.Menu(pickMenu,tearoff=0)
        subsurfacePickMenu = tk.Menu(pickMenu,tearoff=0)

        # surface pick menu items
        surfacePickMenu.add_command(label="new  [ctrl+shift+n]", command=self.start_surf_pick)
        surfacePickMenu.add_command(label="end        [escape]", command=self.end_surf_pick)    
        surfacePickMenu.add_command(label="clear", command=lambda: self.clear(surf = "surface"))    
        pickMenu.add_cascade(label="surface", menu = surfacePickMenu)

        # subsurface pick menu items
        subsurfacePickMenu.add_command(label="new     [ctrl+n]", command=self.start_subsurf_pick)
        subsurfacePickMenu.add_command(label="end     [escape]", command=self.end_subsurf_pick)
        subsurfacePickMenu.add_command(label="clear        [c]", command=lambda: self.clear(surf = "subsurface"))    
        subsurfacePickMenu.add_command(label="clear file", command=self.delete_datafilePicks)            
        pickMenu.add_cascade(label="subsurface", menu = subsurfacePickMenu)  

        # pickMenu.add_separator()
        # pickMenu.add_command(label="Optimize", command=self.nb.select(wav))

        # processing menu items
        procMenu.add_command(label="dewow", command=lambda: self.procTools("dewow"))
        procMenu.add_command(label="remove mean trace", command=lambda: self.procTools("remMnTr"))

        # processing submenu items
        filtMenu = tk.Menu(procMenu,tearoff=0)
        gainMenu = tk.Menu(procMenu,tearoff=0)

        # filtering menu items
        filtMenu.add_command(label="low pass", command=lambda:self.procTools("lowpass"))
        procMenu.add_cascade(label="filter", menu = filtMenu)

        # gain menu items
        gainMenu.add_command(label="agc", command=lambda:self.procTools("agc"))
        gainMenu.add_command(label="t-pow", command=lambda:self.procTools("tpow"))
        procMenu.add_cascade(label="gain", menu = gainMenu)

        # map menu items
        mapMenu.add_command(label="open     [Ctrl+M]", command=self.map_loc)

        # help menu items
        helpMenu.add_command(label="instructions", command=self.help)
        helpMenu.add_command(label="keyboard shortcuts", command=self.shortcuts)

        # add items to menubar
        menubar.add_cascade(label="file", menu=fileMenu)
        menubar.add_cascade(label="pick", menu=pickMenu)
        menubar.add_cascade(label="map", menu=mapMenu)
        menubar.add_cascade(label="processing", menu = procMenu)
        menubar.add_cascade(label="help", menu=helpMenu)
        
        # add the menubar to the window
        self.parent.config(menu=menubar)

        #configure impick and wvpick tabs
        self.nb = ttk.Notebook(self.parent)
        self.nb.pack(side="top",anchor='w', fill="both", expand=1)
        self.imTab = tk.Frame(self.parent)
        self.imTab.pack()
        self.nb.add(self.imTab, text='profile')
        self.wvTab = tk.Frame(self.parent)
        self.wvTab.pack()
        self.nb.add(self.wvTab, text='waveform')

        # bind tab change event to send pick data to wvpick if tab switched from impick
        self.nb.bind("<<NotebookTabChanged>>", self.tab_change)

        # initialize impick
        self.impick = impick.impick(self.imTab)
        self.impick.set_vars()

        # initialize wvpick
        self.wvpick = wvpick.wvpick(self.wvTab)
        self.wvpick.set_vars()

        # bind keypress events
        self.parent.bind("<Key>", self.key)

        # handle x-button closing of window
        self.parent.protocol("WM_DELETE_WINDOW", self.close_window)

        # self.set_home()
        self.open_data()


    # key is a method to handle UI keypress events
    def key(self,event):
        # event.state & 4 True for Ctrl+Key    confDict = ingest.readConfig(argDict)

        # event.state & 1 True for Shift+Key
        # Ctrl+O open file
        if event.state & 4 and event.keysym == "o":
            self.open_data()

        # Ctrl+S save picks
        elif event.state & 4 and event.keysym == "s":
            self.save_loc()

        # Ctrl+M open map
        elif event.state & 4 and event.keysym == "m":
            self.map_loc()

        # Ctrl+N begin subsurface pick
        elif event.state & 4 and event.keysym == "n":
            if self.tab == "profile":
                self.start_subsurf_pick()

        # Ctrl+Shift+N begin surface pick
        elif event.state & 5 == 5 and event.keysym == "N":
            if self.tab == "profile":
                self.start_surf_pick()

        # Ctrl+Q close NOSEpick
        elif event.state & 4 and event.keysym == "q":
            self.close_window()

        elif event.keysym =="Left":
            if self.tab == "waveform":
                self.wvpick.stepBackward()

        # shift+. (>) next file
        elif event.keysym =="Right":
            if self.tab == "profile":
                self.next_loc()
            elif self.tab == "waveform":
                self.wvpick.stepForward()


        # Escape key to stop picking current layer
        elif event.keysym == "Escape":
            if self.tab == "profile":
                self.end_subsurf_pick()
                self.end_surf_pick()

        # c key to clear all picks in impick
        if event.keysym =="c":
            # clear the drawing of line segments
            self.clear(surf = "subsurface")
            
        # BackSpace to clear last pick 
        elif event.keysym =="BackSpace":
            if self.tab == "profile":
                self.impick.clear_last()

        # Space key to toggle impick between radar image and clutter
        elif event.keysym=="space":
            if self.tab == "profile":
                self.impick.set_im()

        # h key to set axes limits to home extent
        elif event.keysym=="h":
            self.impick.set_axes(self.eps_r.get(), self.cmap.get())


    # close_window is a gui method to exit NOSEpick
    def close_window(self):
        # check if picks have been made and saved
        if ((self.impick.get_subsurfPickFlag() == True) or (self.impick.get_surfPickFlag == True)) and (self.f_saveName == ""):
            if tk.messagebox.askokcancel("Warning", "exit NOSEpick without saving picks?", icon = "warning") == True:
                self.parent.destroy()
        else:
            self.parent.destroy()


    # set_home is a method to set the session home directory
    def set_home(self):
        self.datPath = tk.filedialog.askdirectory(title="root data directory",
                                       initialdir=self.datPath,
                                       mustexist=True)    
    

    # set_out is a method to set the session output directory
    def set_out(self):
        self.conf["paths"]["outPath"] = tk.filedialog.askdirectory(title="root directory",
                                       initialdir=self.conf["paths"]["outPath"],
                                       mustexist=True)


    # open_data is a gui method which has the user select and input data file - then passed to impick.load()
    def open_data(self):
        # select input file
        if "linux" in self.os or "win" in self.os:
            temp_loadName = tk.filedialog.askopenfilename(initialdir = self.datPath,title = "select data file",filetypes = (("all files",".*"),("hd5f files", ".mat .h5"),("segy files", ".sgy"),("image file", ".img"),("gssi files",".DZT")))
        else:
            temp_loadName = tk.filedialog.askopenfilename(initialdir = self.datPath,title = "select data file")
        # if input selected, clear impick canvas, ingest data and pass to impick
        if temp_loadName:
            self.f_loadName = temp_loadName
            self.impick.clear_canvas()  
            self.impick.set_vars()
            self.impick.update_option_menu()
            # ingest the data
            self.igst = ingest(self.f_loadName.split(".")[-1])
            self.rdata = self.igst.read(self.f_loadName, self.conf["navigation"]["navcrs"], self.conf["params"]["body"])
            # return if no data ingested
            if not self.rdata:
                return
            self.impick.load(self.rdata)
            self.impick.set_axes(self.eps_r.get(), self.cmap.get())
            self.impick.update_bg()
            self.wvpick.set_vars()
            self.wvpick.clear()
            self.wvpick.set_data(self.rdata)

        # pass basemap to impick for plotting pick location
        if self.map_loadName and self.basemap.get_state() == 1:
            self.basemap.clear_nav()
            self.basemap.set_nav(self.rdata["navdat"], self.f_loadName)
            self.impick.get_basemap(self.basemap)            


    # save_loc is method to receieve the desired pick save location from user input
    def save_loc(self):
        if self.f_loadName:# and ((self.impick.get_subsurfPickFlag() == True) or (self.impick.get_surfPickFlag() == True)):
            if "linux" in self.os or "win" in self.os:
                self.f_saveName = tk.filedialog.asksaveasfilename(initialfile = os.path.splitext(self.f_loadName.split("/")[-1])[0] + "_pk",
                                initialdir = self.conf["paths"]["outPath"], title = "save picks",filetypes = (("comma-separated values","*.csv"),))
            else:
                self.f_saveName = tk.filedialog.asksaveasfilename(initialfile = os.path.splitext(self.f_loadName.split("/")[-1])[0] + "_pk.csv",
                                initialdir = self.conf["paths"]["outPath"], title = "save picks")
        if self.f_saveName:
            self.end_surf_pick()
            self.end_subsurf_pick()
            # get updated pick_dict from wvpick and pass back to impick
            self.impick.set_pickDict(self.wvpick.get_pickDict())
            self.impick.save(self.f_saveName, self.eps_r.get(), self.conf["params"]["amp"], self.cmap.get(), self.figSize.get().split(","))
            self.f_saveName = ""


    # map_loc is a method to get the desired basemap location and initialize
    def map_loc(self):
        tmp_map_loadName = ""
        if "linux" in self.os or "win" in self.os:
            tmp_map_loadName = tk.filedialog.askopenfilename(initialdir = self.conf["paths"]["mapPath"], title = "select basemap file", filetypes = (("geotiff files","*.tif"),("all files","*.*")))
        else:
            tmp_map_loadName = tk.filedialog.askopenfilename(initialdir = self.conf["paths"]["mapPath"], title = "select basemap file")
        if tmp_map_loadName:
            self.map_loadName = tmp_map_loadName
            self.basemap = basemap.basemap(self.parent, self.map_loadName)
            self.basemap.map()

            if self.f_loadName:
                # pass basemap to impick for plotting pick location
                self.basemap.set_nav(self.rdata["navdat"], self.f_loadName)
                self.impick.get_basemap(self.basemap)


    # start_subsurf_pick is a method which begins a new impick pick layer
    def start_subsurf_pick(self):
        if self.f_loadName:
            # end surface picking if currently active
            self.end_surf_pick()
            self.impick.set_pickState(True,surf="subsurface")
            self.impick.pick_interp(surf = "subsurface")
            self.impick.plot_picks(surf = "subsurface")
            # add pick annotations
            self.impick.add_pickLabels()
            self.impick.update_bg()
            self.impick.blit()
            self.impick.update_option_menu()


    # end_subsurf_pick is a method which terminates the current impick pick layer
    def end_subsurf_pick(self):
        if (self.impick.get_pickState() is True) and (self.impick.get_pickSurf() == "subsurface"):
            self.impick.set_pickState(False,surf="subsurface")
            self.impick.pick_interp(surf = "subsurface")
            self.impick.plot_picks(surf = "subsurface")
            # add pick annotations
            self.impick.add_pickLabels()
            self.impick.update_bg()
            self.impick.blit()
            self.impick.update_option_menu()


    # start picking the surface
    def start_surf_pick(self):
        if self.f_loadName:
            # end subsurface picking if currently active
            self.end_subsurf_pick()
            self.impick.set_pickState(True,surf="surface")


    # end surface picking
    def end_surf_pick(self):
        if (self.impick.get_pickState() is True) and (self.impick.get_pickSurf() == "surface"):
            self.impick.set_pickState(False,surf="surface")
            self.impick.pick_interp(surf = "surface")
            self.impick.plot_picks(surf = "surface")
            self.impick.blit()


    # next_loc is a method to get the filename of the next data file in the directory then call impick.load()
    def next_loc(self):
        if self.tab == "profile" and self.f_loadName and self.impick.nextSave_warning() == True:
            # get index of crurrently displayed file in directory
            file_path = self.f_loadName.rstrip(self.f_loadName.split("/")[-1])
            file_list = []

            # step through files in current directory of same extension as currently loaded data
            # determine index of currently loaded data within directory 
            for count,file in enumerate(sorted(glob.glob(file_path + "*." + self.f_loadName.split(".")[-1]))):
                file_list.append(file)
                if file == self.f_loadName:
                    file_index = count

            # add one to index to load next file
            file_index += 1

            # check if more files exist in directory following current file
            if file_index <= (len(file_list) - 1):
                self.f_loadName = file_list[file_index]
                self.impick.clear_canvas()
                self.impick.set_vars()
                self.impick.update_option_menu()
                self.rdata = self.igst.read(self.f_loadName, self.conf["navigation"]["navcrs"], self.conf["params"]["body"])
                # return if no data ingested
                if not self.rdata:
                    return
                self.impick.load(self.f_loadName, self.rdata)
                self.impick.set_axes(self.eps_r.get(), self.cmap.get())
                self.impick.update_bg()
                self.wvpick.clear()
                self.wvpick.set_vars()
                self.wvpick.set_data(self.rdata)

                # if basemap open, update. Only do this if line is longer than certain threshold to now waste time
                if self.map_loadName and self.basemap.get_state() == 1:
                    if self.rdata["dist"][-1] > 5:
                        self.basemap.clear_nav()
                        self.basemap.set_nav(self.rdata["navdat"], self.f_loadName)
                        self.impick.get_basemap(self.basemap)

            else:
                print("Note: " + self.f_loadName.split("/")[-1] + " is the last file in " + file_path + "*." + self.f_loadName.split(".")[-1])


    # load_picks is a method to load and plot picks saved to a csv file
    def load_picks(self):
        if self.f_loadName:
            tmp_loadName = tk.filedialog.askopenfilename(initialdir = self.datPath, title = "load picks", filetypes = (("comma separated value", "*.csv"),))
            if tmp_loadName:
                twtt_bed = ingester.load_picks(path=tmp_loadName)
                self.impick.plot_bed(utils.twtt2sample(twtt_bed, self.rdata["dt"]))


    def tab_change(self, event):
        selection = event.widget.select()
        self.tab = event.widget.tab(selection, "text")
        # determine which tab is active
        if (self.tab == "waveform"):
            if self.f_loadName:
                self.pick_opt()
        elif (self.tab == "profile"):
            # get updated pick_dict and surf_idx from wvpick and pass back to impick if dictionaries differ
            if (self.impick.get_subsurfPickFlag() == True) and (self.dict_compare(self.impick.get_pickDict(),self.wvpick.get_pickDict()) == False) and (tk.messagebox.askyesno("tab change","import optimized picks to profile from waveform?") == True):
                self.impick.set_pickDict(self.wvpick.get_pickDict())
                self.impick.plot_picks(surf = "subsurface")
            # elif (self.impick.get_surfPickFlag() == True):
            if self.f_loadName:
                tmp_surf = self.wvpick.get_surf()
                if ~np.array_equal(self.rdata.surf, tmp_surf):
                    self.rdata.surf = tmp_surf
                    self.rdata.picks["twtt_surf"] = utils.sample2twtt(self.rdata.surf, self.rdata.dt)
                    self.impick.plot_picks(surf = "surface")
            self.impick.blit()


    # pick_opt is a method to load the wvpick optimization tools
    def pick_opt(self):
        # end any picking
        self.end_subsurf_pick()
        self.end_surf_pick()
        # get pick dict from impick and pass to wvpick
        self.wvpick.set_pickDict(self.impick.get_pickDict())
        self.wvpick.plot_wv()


    # dict_compare is a method to compare the subsurface pick dictionaries from wvpick and impick to determine if updates have been made
    def dict_compare(self, dict_impick, dict_wvpick):
        for _i in range(len(dict_impick)):
            if not (np.array_equal(dict_impick[str(_i)] ,dict_wvpick[str(_i)])):
                return False


    # clear is a method to clear all picks
    def clear(self, surf = None):
        if self.f_loadName:
            if (surf == "surface") and (tk.messagebox.askokcancel("warning", "clear all surface picks?", icon = "warning") == True):
                self.impick.clear_picks(surf = "surface")
                self.impick.plot_picks(surf = "surface")
                self.impick.blit()
            elif (self.impick.get_subsurfPickFlag() == True) and (surf == "subsurface") and (tk.messagebox.askokcancel("warning", "clear all subsurface picks?", icon = "warning") == True):
                self.impick.clear_picks(surf = "subsurface")
                self.impick.plot_picks(surf = "subsurface")
                self.impick.update_bg()
                self.impick.blit()
                self.impick.update_option_menu()
                self.wvpick.set_vars()
                self.wvpick.clear()


    # delete_datafilePicks is a method to clear subsurface picks saved to the data file
    def delete_datafilePicks(self):
            if (self.rdata["num_file_pick_lyr"] > 0) and (tk.messagebox.askokcancel("warning", "delte data file subsurface picks?", icon = "warning") == True):
                self.impick.remove_imported_picks()
                self.impick.update_bg()
                self.impick.blit()
                utils.delete_savedPicks(self.f_loadName, self.rdata["num_file_pick_lyr"])
                self.rdata["num_file_pick_lyr"] = 0


    # processing tools
    def procTools(self, arg = None):
        if self.f_loadName:
            if arg == "dewow":
                window = tk.simpledialog.askfloat("input","dewow window size (# samples/" +  str(int(self.rdata["sample"][-1] + 1)) + ")?")
                self.rdata["amp"] = np.abs(processing.dewow(self.rdata["amp"], window=10))
            elif arg == "remMnTr":
                ntraces = int((self.rdata["trace"][-1] + 1)/100)
                self.rdata["amp"] = np.abs(processing.remMeanTrace(self.rdata["amp"], ntraces=ntraces))
            elif arg == "lowpass":
                cutoff = tk.simpledialog.askfloat("input","butterworth filter cutoff frequency?")
                self.rdata["amp"] = np.abs(processing.lowpassFilt(self.rdata["pc"], Wn = cutoff, fs = 1/self.rdata["dt"]))
            elif arg == "agc":
                window = tk.simpledialog.askfloat("input","AGC gain window size (# samples/" +  str(int(self.rdata["sample"][-1] + 1)) + ")?")
                self.rdata["amp"] = processing.agcGain(self.rdata["amp"], window=window)
            elif arg == "tpow":
                power = tk.simpledialog.askfloat("input","power for tpow gain?")
                self.rdata["amp"] = processing.tpowGain(self.rdata["amp"], self.rdata["sample"]*self.rdata["dt"], power=power)
            else:
                print("undefined processing method")
                exit(1)
            self.impick.load(self.f_loadName, self.rdata)
            self.impick.set_axes(self.eps_r.get(), self.cmap.get())
            self.impick.update_bg()
            self.wvpick.clear()
            self.wvpick.set_vars()
            self.wvpick.set_data(self.rdata)


    def settings(self):
        settingsWindow = tk.Toplevel(self.parent)

        row = tk.Frame(settingsWindow)
        row.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        lab = tk.Label(row, width=25, text="user", anchor='w')
        lab.pack(side=tk.LEFT)
        self.userEnt = tk.Entry(row,textvariable=self.userName)
        self.userEnt.pack(side=tk.RIGHT, expand=tk.YES, fill=tk.X)

        row = tk.Frame(settingsWindow)
        row.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        lab = tk.Label(row, width=25, text="dielectric const.", anchor='w')
        lab.pack(side=tk.LEFT)
        self.epsEnt = tk.Entry(row,textvariable=self.eps_r)
        self.epsEnt.pack(side=tk.RIGHT, expand=tk.YES, fill=tk.X)

        row = tk.Frame(settingsWindow)
        row.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        lab = tk.Label(row, width=25, text="export fig. size [w,h]", anchor='w')
        lab.pack(side=tk.LEFT)
        self.figEnt = tk.Entry(row,textvariable=self.figSize)
        self.figEnt.pack(side=tk.RIGHT, expand=tk.YES, fill=tk.X)

        row = tk.Frame(settingsWindow)
        row.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        lab = tk.Label(row, width=25, text="cmap", anchor='w')
        lab.pack(side=tk.LEFT)
        tk.Radiobutton(row,text="greys_r", variable=self.cmap, value="Greys_r").pack(side="top",anchor="w")
        tk.Radiobutton(row,text="gray", variable=self.cmap, value="gray").pack(side="top",anchor="w")
        tk.Radiobutton(row,text="seismic", variable=self.cmap, value="seismic").pack(side="top",anchor="w")

        row = tk.Frame(settingsWindow)
        row.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        lab = tk.Label(row, width=25, text="debug mode", anchor='w')
        lab.pack(side=tk.LEFT)
        tk.Radiobutton(row,text="on", variable=self.debugState, value=True).pack(side="left")
        tk.Radiobutton(row,text="off", variable=self.debugState, value=False).pack(side="left")

        row = tk.Frame(settingsWindow)
        row.pack(side=tk.TOP, anchor='c')
        b1 = tk.Button(row, text='save',
                    command=self.updateSettings)
        b1.pack(side="left")
        b2 = tk.Button(row, text='close', command=settingsWindow.destroy)
        b2.pack(side="left")


    def updateSettings(self):
        self.userName.set(self.userEnt.get())
        self.figSize.set(self.figEnt.get())
        try:
            float(self.epsEnt.get())
            self.eps_r.set(self.epsEnt.get())
        except:
            self.eps_r.set(3.15)

        # make sure fig size is of correct format
        size = self.figSize.get().split(",")
        if len(size) != 2:
            self.figSize.set("21,7")
        try:
            float(size[0])
            float(size[1])
        except:
            self.figSize.set("21,7")
        
        # pass updated dielectric to impick
        self.impick.set_axes(self.eps_r.get(), self.cmap.get())

        # pass updated debug state to impick
        self.impick.set_debugState(self.debugState.get())


    def help(self):
        # help message box
        tk.messagebox.showinfo("instructions",
        """---nearly optimal subsurface extractor---
        \n\n1. file->load to load data file
        \n2. map->open to load basemap
        \n3. pick->surface/subsurface->new to begin\n   new pick segment 
        \n4. click along reflector surface to pick\n   horizon
        \n\t\u2022[backspace] to remove the last
        \n\t\u2022[c] to remove all subsurface\n\t picks
        \n5. pick->surface/subsurface->stop to end\n   current pick segment
        \n6. radio buttons to toggle between radar\n   and clutter images
        \n7. file->save to export picks
        \n8. file->next to load next data file
        \n9. file->quit to exit application""")


    def shortcuts(self):
        # shortcut list
        tk.messagebox.showinfo("keyboard shortcuts",
        """---general---
        \n[ctrl+o]\topen radar data file
        \n[ctrl+m]\topen basemap window
        \n[spacebar]\ttoggle between radar and\n\t\tclutter images
        \n[h]\t\treturn to home extent
        \n[ctrl+s]\texport pick data
        \n[→]\t\topen next file in\n\t\tworking directory
        \n[ctrl+q]\tquit NOSEpick
        \n\n---picking---
        \n[ctrl+n]\tbegin new subsurface pick\n\t\tsegment
        \n[ctrl+shift+n]\tbegin new surface pick\n\t\tsegment
        \n[escape]\tend current surface/\n\t\tsubsurface pick segment
        \n[backspace]\tremove last pick event
        \n[c]\t\tremove all picked\n\t\tsubsurface segments""")