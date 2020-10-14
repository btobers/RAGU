"""
NOSEpick - Nearly Optimal Subsurface Extractor
created by: Brandon S. Tober and Michael S. Christoffersen
date: 25JUN19
last updated: 05FEB20
environment requirements in nose_env.yml

mainGUI class is a tkinter frame which runs the NOSEpick master GUI
"""
### imports ###
from ui import impick, wvpick, basemap 
from tools import utils, export
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
            self.datPath = self.conf["path"]["datPath"]
        # initialize variables
        self.rdata = None
        self.f_loadName = ""
        self.f_saveName = ""
        self.map_loadName = ""
        self.tab = "profile"
        self.eps_r = tk.DoubleVar(value=self.conf["output"]["eps_r"])
        self.figSize = tk.StringVar(value="21,7")
        self.cmap = tk.StringVar(value="Greys_r")
        self.debugState = tk.BooleanVar()
        self.debugState.set(False)
        self.os = sys.platform
        # setup tkinter frame
        self.setup()


    # setup is a method which generates the app menubar and buttons and initializes some vars
    def setup(self):
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
        fileMenu.add_command(label="load picks", command=self.import_picks)
        fileMenu.add_command(label="next        [right]", command=self.next_loc)

        # import submenu
        importMenu = tk.Menu(fileMenu,tearoff=0)
        importMenu.add_command(label="picks", command=self.import_picks)

        fileMenu.add_cascade(label="import", menu = importMenu)

        # export submenu
        exportMenu = tk.Menu(fileMenu,tearoff=0)
        exportMenu.add_command(label="picks       [ctrl+s]", command=self.savePicks)
        exportMenu.add_command(label="processed data", command=self.saveProc)

        fileMenu.add_cascade(label="export", menu = exportMenu)

        # settings submenu
        settingsMenu = tk.Menu(fileMenu,tearoff=0)
        settingsMenu.add_command(label="preferences", command=self.settings)
        settingsMenu.add_command(label="set working folder", command=self.set_home)
        settingsMenu.add_command(label="set output folder", command=self.set_out)

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
        pickMenu.add_command(label="import", command=self.import_picks)
        pickMenu.add_command(label="export  [ctrl+s]", command=self.savePicks)

        # pickMenu.add_separator()
        # pickMenu.add_command(label="Optimize", command=self.nb.select(wav))

        # processing menu items
        procMenu.add_command(label="set time zero", command=lambda: self.procTools("tzero"))
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

        procMenu.add_command(label="restore original data", command=lambda:self.procTools("restore"))

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

        # configure impick and wvpick tabs
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
        self.impick = impick.impick(self.imTab, self.cmap.get(), self.eps_r.get())
        self.impick.set_vars()

        # initialize wvpick
        self.wvpick = wvpick.wvpick(self.wvTab)
        self.wvpick.set_vars()

        # handle x-button closing of window
        self.parent.protocol("WM_DELETE_WINDOW", self.close_window)

        # bind keypress events
        self.parent.bind("<Key>", self.key)

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
            self.savePicks()

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

        # Space key to toggle impick between radar image and sim
        elif event.keysym=="space":
            if self.tab == "profile":
                self.impick.set_im()

        # h key to set axes limits to home extent
        elif event.keysym=="h":
            self.impick.fullExtent()

        # r key to set axes limits to home extent
        elif event.keysym=="d":
            self.impick.panRight()

        # l key to set axes limits to home extent
        elif event.keysym=="a":
            self.impick.panLeft()

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
        self.conf["path"]["outPath"] = tk.filedialog.askdirectory(title="output data directory",
                                       initialdir=self.conf["path"]["outPath"],
                                       mustexist=True)


    # open_data is a gui method which has the user select and input data file - then passed to impick.load()
    def open_data(self, temp_loadName=None):
        # try:
            # prompt save warning if picks exist
        if self.impick.saveWarning() == True:
            if not temp_loadName:
                # select input file
                if self.os == "darwin":
                    temp_loadName = tk.filedialog.askopenfilename(initialdir = self.datPath,title = "select data file")
                else:
                    temp_loadName = tk.filedialog.askopenfilename(initialdir = self.datPath,title = "select data file",filetypes = [("all files",".*"),
                                                                                                                                    ("hd5f", ".mat .h5"),
                                                                                                                                    ("segy", ".sgy"),
                                                                                                                                    ("sharad", ".img"),
                                                                                                                                    ("marsis", ".dat"),
                                                                                                                                    ("gssi",".DZT")])
            # if input selected, clear impick canvas, ingest data and pass to impick
            if temp_loadName:
                # ensure we're on profile tab
                if self.tab == "waveform":
                    self.nb.select(self.nb.tabs()[0])
                self.f_loadName = temp_loadName
                self.f_saveName = ""
                self.impick.clear_canvas()  
                self.impick.set_vars()
                self.impick.update_option_menu()
                # ingest the data
                self.igst = ingest(self.f_loadName.split(".")[-1])
                self.rdata = self.igst.read(self.f_loadName, self.conf["path"]["simPath"], self.conf["nav"]["crs"], self.conf["nav"]["body"])
                # return if no data ingested
                if not self.rdata:
                    return
                self.impick.load(self.rdata)
                self.impick.set_axes()
                self.impick.drawData()
                self.impick.update_bg()
                self.wvpick.set_vars()
                self.wvpick.clear()
                self.wvpick.set_data(self.rdata)

            # pass basemap to impick for plotting pick location
            if self.map_loadName and self.basemap.get_state() == 1:
                self.basemap.set_track(self.rdata.fn)
                self.basemap.set_nav(self.rdata.fn, self.rdata.navdf)
                self.basemap.plot_tracks()
                self.impick.get_basemap(self.basemap)

        # recall open_data if wrong file type is selected 
        # except Exception as err:
        #     print(err)
        #     self.open_data() 


    # savePicks is method to receieve the desired pick save location from user input
    def savePicks(self):
        if self.f_loadName:# and ((self.impick.get_subsurfPickFlag() == True) or (self.impick.get_surfPickFlag() == True)):
            tmp_fn_out = ""
            if self.os == "darwin":
                tmp_fn_out = tk.filedialog.asksaveasfilename(initialfile = os.path.splitext(self.f_loadName.split("/")[-1])[0] + "_pk",
                                initialdir = self.conf["path"]["outPath"], title = "save picks")
                                
            else:
                tmp_fn_out = tk.filedialog.asksaveasfilename(initialfile = os.path.splitext(self.f_loadName.split("/")[-1])[0] + "_pk",
                                initialdir = self.conf["path"]["outPath"], title = "save picks", filetypes = [("all files", ".*"),
                                                                                                            ("comma-separated values",".csv"),
                                                                                                            ("esri shapefile", ".shp")])


            if tmp_fn_out:
                self.f_saveName, ext = os.path.splitext(tmp_fn_out)

                # end any current pick segments
                self.end_surf_pick()
                self.end_subsurf_pick()
                # set output dataframe
                self.rdata.set_out(export.pick_math(self.rdata, self.eps_r.get(), self.conf["output"]["amp"]))

                # export
                if (self.conf["output"]["csv"]) or (ext == ".csv"):
                    export.csv(self.f_saveName + ".csv", self.rdata.out)
                if (self.conf["output"]["shp"]) or (ext == ".shp"):
                    export.shp(self.f_saveName + ".shp", self.rdata.out, self.conf["nav"]["crs"])
                if self.rdata.fpath.endswith(".h5") and (tk.messagebox.askyesno("export picks", "save picks to data file?") == True):
                    export.h5(self.rdata.fpath, self.rdata.out)
                if self.conf["output"]["fig"]:
                    self.impick.save_fig(self.f_saveName, self.figSize.get().split(","))


    # saveProc is a method to save processed radar data
    def saveProc(self):
        if self.f_loadName:
            tmp_fn_out = ""
            if self.os == "darwin":
                tmp_fn_out = tk.filedialog.asksaveasfilename(initialfile = os.path.splitext(self.f_loadName.split("/")[-1])[0] + "_proc.csv",
                                initialdir = self.conf["path"]["outPath"], title = "save processed data")
            else:
                tmp_fn_out = tk.filedialog.asksaveasfilename(initialfile = os.path.splitext(self.f_loadName.split("/")[-1])[0] + "_proc",
                                initialdir = self.conf["path"]["outPath"], title = "save processed data", filetypes = [("comma-separated values",".csv")])
            if tmp_fn_out:
                fn, ext = os.path.splitext(tmp_fn_out)

                export.proc(fn + ".csv", self.rdata.proc)


    # map_loc is a method to get the desired basemap location and initialize
    def map_loc(self):
        tmp_map_loadName = ""
        if "linux" in self.os or "win" in self.os:
            tmp_map_loadName = tk.filedialog.askopenfilename(initialdir = self.conf["path"]["mapPath"], title = "select basemap file", filetypes = [("geotiff files","*.tif"),
                                                                                                                                                    ("all files","*.*")])
        else:
            tmp_map_loadName = tk.filedialog.askopenfilename(initialdir = self.conf["path"]["mapPath"], title = "select basemap file")
        if tmp_map_loadName:
            # initialize basemap if not currently open
            if not self.map_loadName or self.basemap.get_state() == 0:
                self.basemap = basemap.basemap(self.parent, self.datPath, self.conf["nav"]["crs"], self.conf["nav"]["body"], self.from_basemap)
            self.map_loadName = tmp_map_loadName
            self.basemap.set_vars()
            self.basemap.map(self.map_loadName)

            if self.f_loadName:
                # pass basemap to impick for plotting pick location
                self.basemap.clear_nav()
                self.basemap.set_track(self.rdata.fn)
                self.basemap.set_nav(self.rdata.fn, self.rdata.navdf)
                self.basemap.plot_tracks()
                self.impick.get_basemap(self.basemap)


    # return selected track from basemap frame
    def from_basemap(self, path, track):
        # find matching file to pass to open_loc - ensure valid ftype
        f = [_i for _i in os.listdir(path) if track in _i]
        for _i in f:
            try:
                ingest(_i.split(".")[-1])
                break
            except Exception:
                continue

        # pass file to open_data
        self.open_data(path + _i)


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
            self.impick.update_bg()
            # update gnd_elevation
            self.rdata.set_gndElev(utils.srfpick2elev(self.rdata.pick.current_surf, 
                                                      self.rdata.navdf["elev"].to_numpy(), 
                                                      self.rdata.tnum,
                                                      self.rdata.dt))


    # next_loc is a method to get the filename of the next data file in the directory then call impick.load()
    def next_loc(self):
        if self.tab == "profile" and self.f_loadName and self.impick.saveWarning() == True:
            # get index of crurrently displayed file in directory
            file_path = self.f_loadName.rstrip(self.f_loadName.split("/")[-1])
            file_list = []

            # step through files in current directory of same extension as currently loaded data
            # determine index of currently loaded data within directory 
            for count,file in enumerate(sorted(glob.glob(file_path + "*." + self.igst.ftype))):
                file_list.append(file)
                if file == self.f_loadName:
                    file_index = count

            # add one to index to load next file
            file_index += 1

            # check if more files exist in directory following current file
            if file_index <= (len(file_list) - 1):
                self.f_loadName = file_list[file_index]
                self.f_saveName = ""
                self.impick.clear_canvas()
                self.impick.set_vars()
                self.impick.update_option_menu()
                self.rdata = self.igst.read(self.f_loadName, self.conf["path"]["simPath"], self.conf["nav"]["crs"], self.conf["nav"]["body"])
                # return if no data ingested
                if not self.rdata:
                    return
                self.impick.load(self.rdata)
                self.impick.set_axes()
                self.impick.drawData()
                self.impick.update_bg()
                self.wvpick.clear()
                self.wvpick.set_vars()
                self.wvpick.set_data(self.rdata)

                # if basemap open, update. Only do this if line is longer than certain threshold to now waste time
                if self.map_loadName and self.basemap.get_state() == 1:
                    self.basemap.set_track(self.rdata.fn)
                    self.basemap.set_nav(self.rdata.fn, self.rdata.navdf)
                    self.basemap.plot_tracks()
                    self.impick.get_basemap(self.basemap)

            else:
                print("Note: " + self.f_loadName.split("/")[-1] + " is the last file in " + file_path + "*." + self.f_loadName.split(".")[-1])


    # import_picks is a method to load and plot picks saved to a csv file
    def import_picks(self):
        if self.f_loadName:
            pk_file = ""
            pk_file = tk.filedialog.askopenfilename(initialdir = self.conf["path"]["outPath"], title = "load picks", filetypes = (("comma separated value", "*.csv"),))
            if pk_file:
                self.igst.import_picks(pk_file)
                self.impick.plot_existing(surf = "subsurface")
                self.impick.blit()


    # change tabs between profile and waveform views
    def tab_change(self, event):
        selection = event.widget.select()
        self.tab = event.widget.tab(selection, "text")
        if self.rdata:
            # determine which tab is active
            if (self.tab == "waveform"):
                if self.f_loadName:
                    # end any picking
                    self.end_subsurf_pick()
                    self.end_surf_pick()
                    # get pick dict from impick and pass to wvpick
                    self.wvpick.set_picks()
                    self.wvpick.plot_wv()
            elif (self.tab == "profile"):
                # get updated picks from wvpick and pass back to impick if they differ
                if (((utils.nan_array_equal(self.rdata.pick.current_surf, self.rdata.pick.current_surfOpt)) == False) or \
                        ((utils.dict_compare(self.rdata.pick.current_subsurf, self.rdata.pick.current_subsurfOpt)) == False)) and \
                        (tk.messagebox.askyesno("tab change","import optimized picks to profile from waveform?") == True):
                    self.rdata.pick.current_surf = self.rdata.pick.current_surfOpt
                    # update gnd_elevation
                    self.rdata.set_gndElev(utils.srfpick2elev(self.rdata.pick.current_surf, 
                                                            self.rdata.navdf["elev"].to_numpy(), 
                                                            self.rdata.tnum,
                                                            self.rdata.dt))
                    self.rdata.pick.current_subsurf = self.rdata.pick.current_subsurfOpt
                    self.impick.set_picks()
                    self.impick.blit()


    # clear is a method to clear all picks
    def clear(self, surf = None):
        if self.f_loadName:
            if (surf == "surface") and (tk.messagebox.askokcancel("warning", "clear all surface picks?", icon = "warning") == True):
                # reset current surf pick array
                self.rdata.pick.current_surf.fill(np.nan)
                # reset surf pick flag
                self.impick.clear_surfPicks()
                self.impick.plot_picks(surf = "surface")
                self.impick.update_bg()
            elif (self.impick.get_subsurfPickFlag() == True) and (surf == "subsurface") and (tk.messagebox.askokcancel("warning", "clear all subsurface picks?", icon = "warning") == True):
                # clear current subsurf pick dictionaries
                self.rdata.pick.current_subsurf.clear()
                self.rdata.pick.current_subsurfOpt.clear()
                self.impick.clear_subsurfPicks()
                self.impick.plot_picks(surf = "subsurface")
                self.impick.update_bg()
                self.impick.update_option_menu()
                self.wvpick.set_vars()
                self.wvpick.clear()


    # delete_datafilePicks is a method to clear subsurface picks saved to the data file
    def delete_datafilePicks(self):
            if self.f_loadName and tk.messagebox.askokcancel("warning", "delte any existing data file subsurface picks?", icon = "warning") == True:
                utils.delete_savedPicks(self.f_loadName)
                self.impick.remove_existing_subsurf()
                self.impick.update_bg()


    # processing tools
    def procTools(self, arg = None):
        print("WARNING:\tprocessing tools are still in development!")
        if self.f_loadName:
            procFlag = False
            if arg == "tzero":
                sampzero, proc = processing.set_tzero(self.rdata.dat, self.rdata.proc, self.rdata.dt)
                if sampzero > 0:
                    self.rdata.flags.sampzero = sampzero
                    # set current surface pick to index zer
                    self.rdata.pick.current_surf.fill(0)
                    self.impick.set_picks()
                    self.impick.blit()
                    procFlag = True

            elif arg == "dewow":
                print("dewow currently in development")
                # window = tk.simpledialog.askfloat("input","dewow window size (# samples/" +  str(int(self.rdata.snum)) + ")?")
                # proc = processing.dewow(self.rdata.dat, window=10)
                # procFlag = True

            elif arg == "remMnTr":
                print("mean trace removal currently in development")
                # nraces = tk.simpledialog.askfloat("input","moving average window size (# traces/" +  str(int(self.rdata.tnum)) + ")?")
                # proc = processing.remMeanTrace(self.rdata.dat, ntraces=ntraces)
                # procFlag = True

            elif arg == "lowpass":
                cutoff = tk.simpledialog.askfloat("input","butterworth filter cutoff frequency?")
                proc = processing.lowpassFilt(self.rdata.dat, Wn = cutoff, fs = 1/self.rdata.dt)
                procFlag = True

            elif arg == "agc":
                print("automatic gain control currently in development")
                # window = tk.simpledialog.askfloat("input","AGC gain window size (# samples/" +  str(int(self.rdata.snum)) + ")?")
                # proc = processing.agcGain(self.rdata.dat, window=window)
                # procFlag = True

            elif arg == "tpow":
                power = tk.simpledialog.askfloat("input","power for tpow gain?")
                proc = processing.tpowGain(np.abs(self.rdata.dat), np.arange(self.rdata.snum)*self.rdata.dt, power=power)
                procFlag = True

            elif arg == "restore":
                # restore origianl rdata
                proc = processing.restore(self.rdata.dtype, self.rdata.dat)
                procFlag = True

            else:
                print("undefined processing method")
                exit(1)

            if procFlag:
                self.rdata.set_proc(proc)
                self.impick.set_crange()
                self.impick.drawData(force=True)
                self.wvpick.clear()
                self.wvpick.set_vars()
                self.wvpick.set_data(self.rdata)


    def settings(self):
        settingsWindow = tk.Toplevel(self.parent)

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
        self.impick.set_eps_r(self.eps_r.get())
        self.impick.set_axes()

        # pass cmap
        self.impick.set_cmap(self.cmap.get())

        # pass updated debug state to impick
        self.impick.set_debugState(self.debugState.get())

        # draw images
        self.impick.drawData()


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
        \n[a]\t\tpan left
        \n[d]\t\tpan right
        \n[ctrl+s]\texport pick data
        \n[→]\t\topen next file in\n\t\tworking directory
        \n[ctrl+q]\tquit NOSEpick
        \n\n---picking---
        \n[ctrl+n]\tbegin new subsurface pick\n\t\tsegment
        \n[ctrl+shift+n]\tbegin new surface pick\n\t\tsegment
        \n[escape]\tend current surface/\n\t\tsubsurface pick segment
        \n[backspace]\tremove last pick event
        \n[c]\t\tremove all picked\n\t\tsubsurface segments""")