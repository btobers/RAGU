# RAGU - Radar Analysis Graphical Utility
#
# copyright © 2020 btobers <tobers.brandon@gmail.com>
#
# distributed under terms of the GNU GPL3.0 license
"""
RAGU - Radar Analysis Graphical Utility
created by: Brandon S. Tober and Michael S. Christoffersen
date: 25JUN19
last updated: 05FEB20
environment requirements in nose_env.yml

mainGUI class is a tkinter frame which runs the RAGU master GUI
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
        # dictionary to hold figure settings
        self.figsettings = {"cmap": tk.StringVar(value="Greys_r"),
                            "figsize": tk.StringVar(value="6.5,1.5"), 
                            "fontsize": tk.DoubleVar(value="12"),
                            "figtitle": tk.BooleanVar(),
                            "figxaxis": tk.BooleanVar(),
                            "figyaxis": tk.BooleanVar(),
                            "figclip": tk.DoubleVar(value=1.0)}
        self.figsettings["figxaxis"].set(True)        
        self.figsettings["figyaxis"].set(True)        
        self.figsettings["figtitle"].set(True)        
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
        # |  |-next
        # |  |-import
        # |  |-save
        # |  |  |-picks
        # |  |  |-figure
        # |  |  |-processed data
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
        # open submenu
        openMenu = tk.Menu(fileMenu,tearoff=0)
        openMenu.add_command(label="data file    [ctrl+o]", command=self.open_data)
        openMenu.add_command(label="basemap  [ctrl+m]", command=self.map_loc)
        fileMenu.add_cascade(label="open", menu = openMenu)

        fileMenu.add_command(label="next      [→]", command=self.next_loc)

        # save submenu
        saveMenu = tk.Menu(fileMenu,tearoff=0)
        saveMenu.add_command(label="picks      [ctrl+s]", command=self.savePicks)
        saveMenu.add_command(label="figure", command=self.saveFig)
        saveMenu.add_command(label="processed data", command=self.saveProc)
        fileMenu.add_cascade(label="save", menu = saveMenu)
        fileMenu.add_separator()

        # settings submenu
        settingsMenu = tk.Menu(fileMenu,tearoff=0)
        settingsMenu.add_command(label="preferences", command=self.settings)
        settingsMenu.add_command(label="set working folder", command=self.set_home)
        settingsMenu.add_command(label="set output folder", command=self.set_out)

        fileMenu.add_cascade(label="settings", menu = settingsMenu)
        fileMenu.add_separator()
    
        fileMenu.add_command(label="exit  [ctrl+q]", command=self.close_window)

        # pick menu subitems
        surfacePickMenu = tk.Menu(pickMenu,tearoff=0)
        subsurfacePickMenu = tk.Menu(pickMenu,tearoff=0)

        # surface pick menu items
        surfacePickMenu.add_command(label="new  [ctrl+shift+n]", command=self.start_surf_pick)
        surfacePickMenu.add_command(label="end       [escape]", command=self.end_surf_pick)    
        surfacePickMenu.add_command(label="clear", command=lambda: self.clear(surf = "surface"))    
        pickMenu.add_cascade(label="surface", menu = surfacePickMenu)

        # subsurface pick menu items
        subsurfacePickMenu.add_command(label="new     [ctrl+n]", command=self.start_subsurf_pick)
        subsurfacePickMenu.add_command(label="end   [escape]", command=self.end_subsurf_pick)
        subsurfacePickMenu.add_command(label="clear          [c]", command=lambda: self.clear(surf = "subsurface"))    
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

        procMenu.add_command(label="shift sim", command=lambda: self.procTools("shiftSim"))
        procMenu.add_command(label="restore original data", command=lambda:self.procTools("restore"))

        # help menu items
        helpMenu.add_command(label="instructions", command=self.help)
        helpMenu.add_command(label="keyboard shortcuts", command=self.shortcuts)

        # add items to menubar
        menubar.add_cascade(label="file", menu=fileMenu)
        menubar.add_cascade(label="pick", menu=pickMenu)
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
        self.impick = impick.impick(self.imTab, self.figsettings)
        self.impick.set_eps_r(self.eps_r.get())
        self.impick.set_vars()

        # initialize wvpick
        self.wvpick = wvpick.wvpick(self.wvTab)
        self.wvpick.set_vars()

        # set up  info frame
        infoFrame = tk.Frame(self.parent)
        infoFrame.pack(side="bottom",fill="both")

        self.siglbl = tk.Label(infoFrame, text="signal type: ", font= "Verdana 10")
        self.siglbl.pack(side="left")

        # handle x-button closing of window
        self.parent.protocol("WM_DELETE_WINDOW", self.close_window)

        # bind keypress events
        self.parent.bind("<Key>", self.key)

        self.open_data()


    # key is a method to handle UI keypress events
    def key(self,event):
        # event.state & 4 True for Ctrl+Key
        # event.state & 1 True for Shift+Key
        # general keps for either tab
        # Ctrl+O open file
        if event.state & 4 and event.keysym == "o":
            self.open_data()

        # Ctrl+S save picks
        elif event.state & 4 and event.keysym == "s":
            self.savePicks()

        # Ctrl+M open map
        elif event.state & 4 and event.keysym == "m":
            self.map_loc()

        # Ctrl+Q close RAGU
        elif event.state & 4 and event.keysym == "q":
            self.close_window()

        # profile view keys
        if self.tab == "profile":
            # Space key to toggle impick between radar image and sim
            if event.keysym=="space":
                self.impick.set_im()

            elif event.state & 4 and event.keysym == "n":
                self.start_subsurf_pick()

            # Ctrl+Shift+N begin surface pick
            elif event.state & 5 == 5 and event.keysym == "N":
                self.start_surf_pick()

            # Escape key to stop picking current layer
            elif event.keysym == "Escape":
                    self.end_subsurf_pick()
                    self.end_surf_pick()

            # BackSpace to clear last pick 
            elif event.keysym =="BackSpace":
                self.impick.clear_last()

            # c key to clear all picks in impick
            elif event.keysym =="c":
                # clear the drawing of line segments
                self.clear(surf = "subsurface")

            # right key next file
            elif event.keysym =="Right":
                self.next_loc()

            # h key to set axes limits to home extent
            elif event.keysym=="h":
                self.impick.fullExtent()

            # d key to set axes limits to home extent
            elif event.keysym=="d":
                self.impick.panRight()

            # a key to set axes limits to home extent
            elif event.keysym=="a":
                self.impick.panLeft()

            # w key to set axes limits to home extent
            elif event.keysym=="w":
                self.impick.panUp()

            # s key to set axes limits to home extent
            elif event.keysym=="s":
                self.impick.panDown()

        # waveform view keys
        if self.tab == "waveform":
            # h key to set axes limits to home extent
            if event.keysym=="h":
                self.wvpick.fullExtent()
    
            # a key to step back in trace count
            elif event.keysym=="Right":
                self.wvpick.stepForward()

            # d key to step forward in trace count
            elif event.keysym=="Left":
                self.wvpick.stepBackward()


    # saveCheck is a method to check if picks have been saved
    def save_check(self):
        if ((self.impick.get_subsurfpkFlag() == True) or (self.impick.get_surfpkFlag() == True)) and (self.rdata.out is None):
            return False
        else:
            return True


    # close_window is a gui method to exit RAGU
    def close_window(self):
        # check if picks have been made and saved
        if self.save_check() == False:
            if tk.messagebox.askokcancel("Warning", "exit RAGU without saving picks?", icon = "warning") == True:
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
        try:
            # prompt save check
            if (self.save_check() == False) and (tk.messagebox.askyesno("Warning", "Discard unsaved picks?", icon = "warning") == False):
                return
            else:
                if not temp_loadName:
                    # select input file
                    if self.os == "darwin":
                        temp_loadName = tk.filedialog.askopenfilename(initialdir = self.datPath,title = "select data file")
                    else:
                        temp_loadName = tk.filedialog.askopenfilename(initialdir = self.datPath,title = "select data file",filetypes = [("all files",".*"),
                                                                                                                                        ("hd5f", ".mat .h5"),
                                                                                                                                        ("sharad", ".img"),
                                                                                                                                        ("marsis", ".dat"),
                                                                                                                                        ("pulseekko", ".DT1"),
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
                    self.impick.update_figsettings(self.figsettings)
                    self.impick.set_axes()
                    self.impick.drawData()
                    self.impick.update_bg()
                    self.wvpick.set_vars()
                    self.wvpick.clear()
                    self.wvpick.set_data(self.rdata)
                    self.siglbl.config(text = '\t\t'.join('{}: {}'.format(k, d) for k, d in self.rdata.sig.items()))

                # pass basemap to impick for plotting pick location
                if self.map_loadName and self.basemap.get_state() == 1:
                    self.basemap.set_track(self.rdata.fn)
                    self.basemap.set_nav(self.rdata.fn, self.rdata.navdf)
                    self.basemap.plot_tracks()
                    self.impick.get_basemap(self.basemap)

        # recall open_data if wrong file type is selected 
        except Exception as err:
            print(err)
            self.open_data() 


    # next_loc is a method to get the filename of the next data file in the directory then call impick.load()
    def next_loc(self):
        if self.tab == "profile" and self.f_loadName:
            # prompt save check
            if (self.save_check() == False) and (tk.messagebox.askyesno("Warning", "Discard unsaved picks?", icon = "warning") == False):
                return
            else:
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
                    self.impick.update_figsettings(self.figsettings)
                    self.impick.set_axes()
                    self.impick.drawData()
                    self.impick.update_bg()
                    self.wvpick.clear()
                    self.wvpick.set_vars()
                    self.wvpick.set_data(self.rdata)
                    self.siglbl.config(text = '\t\t'.join('{}: {}'.format(k, d) for k, d in self.rdata.sig.items()))

                    # if basemap open, update. Only do this if line is longer than certain threshold to now waste time
                    if self.map_loadName and self.basemap.get_state() == 1:
                        self.basemap.set_track(self.rdata.fn)
                        self.basemap.set_nav(self.rdata.fn, self.rdata.navdf)
                        self.basemap.plot_tracks()
                        self.impick.get_basemap(self.basemap)

                else:
                    print("Note: " + self.f_loadName.split("/")[-1] + " is the last file in " + file_path + "*." + self.f_loadName.split(".")[-1])


    # savePicks is method to receieve the desired pick save location from user input
    def savePicks(self):
        if self.f_loadName:
            # see if picks have been made
            if (self.impick.get_subsurfpkFlag() == True) or (self.impick.get_surfpkFlag() == True):
                fn = self.rdata.fn + "_pk_" + self.conf["param"]["uid"]
            else:
                fn = self.rdata.fn

            tmp_fn_out = ""
            if self.os == "darwin":
                tmp_fn_out = tk.filedialog.asksaveasfilename(initialfile = fn,
                                initialdir = self.conf["path"]["outPath"], title = "save picks")
                                
            else:
                tmp_fn_out = tk.filedialog.asksaveasfilename(initialfile = fn,
                                initialdir = self.conf["path"]["outPath"], title = "save picks", filetypes = [("all files", ".*"),
                                                                                                            ("comma-separated values",".csv"),
                                                                                                            ("esri shapefile", ".shp"),
                                                                                                            ("png image", ".png")])

            if tmp_fn_out:
                self.f_saveName, ext = os.path.splitext(tmp_fn_out)

                # end any current pick segments
                self.end_surf_pick()
                self.end_subsurf_pick()
                # set output dataframe
                self.rdata.set_out(export.pick_math(self.rdata, self.eps_r.get(), self.conf["output"]["amp"]))

                # export
                if (self.conf["output"].getboolean("csv")) or (ext == ".csv"):
                    export.csv(self.f_saveName + ".csv", self.rdata.out)
                if (self.conf["output"].getboolean("shp")) or (ext == ".shp"):
                    export.shp(self.f_saveName + ".shp", self.rdata.out, self.conf["nav"]["crs"])
                if (self.conf["output"].getboolean("fig")) or (ext == ".png"):
                    self.impick.save_fig(self.f_saveName + ".png")
                # if (self.rdata.fpath.endswith(".h5")) and (tk.messagebox.askyesno("export picks", "save picks to data file?") == True):
                #     export.h5(self.rdata.fpath, self.rdata.out)


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


    # saveFig is a method to export the radargram image
    def saveFig(self):
        if self.f_loadName:
            tmp_fn_out = ""
            if self.os == "darwin":
                tmp_fn_out = tk.filedialog.asksaveasfilename(initialfile = os.path.splitext(self.f_loadName.split("/")[-1])[0] + ".png",
                                initialdir = self.conf["path"]["outPath"], title = "save radar image")
            else:
                tmp_fn_out = tk.filedialog.asksaveasfilename(initialfile = os.path.splitext(self.f_loadName.split("/")[-1])[0],
                                initialdir = self.conf["path"]["outPath"], title = "save radar image", filetypes = [("png image", ".png")])
            if tmp_fn_out:
                fn, ext = os.path.splitext(tmp_fn_out)

            self.impick.save_fig(fn + ".png")


    # map_loc is a method to get the desired basemap location and initialize
    def map_loc(self):
        tmp_map_loadName = ""
        if self.os == "darwin":
            tmp_map_loadName = tk.filedialog.askopenfilename(initialdir = self.conf["path"]["mapPath"], title = "select basemap file")

        else:
            tmp_map_loadName = tk.filedialog.askopenfilename(initialdir = self.conf["path"]["mapPath"], title = "select basemap file", filetypes = [("geotiff files","*.tif"),
                                                                                                                                                    ("all files","*.*")])
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
            elif (self.impick.get_subsurfpkFlag() == True) and (surf == "subsurface") and (tk.messagebox.askokcancel("warning", "clear all subsurface picks?", icon = "warning") == True):
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
        if self.f_loadName:
            procFlag = None
            simFlag = None
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

            elif arg == "shiftSim":
                shift = tk.simpledialog.askinteger("input","clutter sim lateral shift (# traces)?")
                if shift:
                    sim = processing.shiftSim(self.rdata.sim, shift)
                    self.rdata.flags.simshift += shift
                    simFlag = True
                    print("clutter simulation shifted by a total of " + str(self.rdata.flags.simshift) + " traces, or " + str(self.rdata.flags.simshift * self.rdata.sig["prf [kHz]"] * 1e3) + " seconds")

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

            if simFlag:
                self.rdata.set_sim(utils.powdB2amp(sim))
                self.impick.set_crange()
                self.impick.drawData(force=True)


    def settings(self):
        settingsWindow = tk.Toplevel(self.parent)

        row = tk.Frame(settingsWindow)
        row.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        label = tk.Label(row, text = "general")
        label.pack(side=tk.TOP)
        f = tk.font.Font(label, label.cget("font"))
        f.configure(underline=True)
        label.configure(font=f)

        row = tk.Frame(settingsWindow)
        row.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        lab = tk.Label(row, width=25, text="dielectric const.", anchor='w')
        lab.pack(side=tk.LEFT)
        self.epsEnt = tk.Entry(row,textvariable=self.eps_r)
        self.epsEnt.pack(side=tk.RIGHT, expand=tk.YES, fill=tk.X)

        row = tk.Frame(settingsWindow)
        row.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        lab = tk.Label(row, width=25, text="debug mode", anchor='w')
        lab.pack(side=tk.LEFT)
        tk.Radiobutton(row,text="on", variable=self.debugState, value=True).pack(side="left")
        tk.Radiobutton(row,text="off", variable=self.debugState, value=False).pack(side="left")

        row = tk.Frame(settingsWindow)
        row.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        label = tk.Label(row, text = "image")
        label.pack(side=tk.TOP)
        f = tk.font.Font(label, label.cget("font"))
        f.configure(underline=True)
        label.configure(font=f)

        row = tk.Frame(settingsWindow)
        row.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        lab = tk.Label(row, width=25, text="color map", anchor='w')
        lab.pack(side=tk.LEFT)
        tk.Radiobutton(row,text="greys_r", variable=self.figsettings["cmap"], value="Greys_r").pack(side="top",anchor="w")
        tk.Radiobutton(row,text="gray", variable=self.figsettings["cmap"], value="gray").pack(side="top",anchor="w")
        tk.Radiobutton(row,text="seismic", variable=self.figsettings["cmap"], value="seismic").pack(side="top",anchor="w")

        row = tk.Frame(settingsWindow)
        row.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        lab = tk.Label(row, width=25, text="fig. size [w,h]", anchor='w')
        lab.pack(side=tk.LEFT)
        self.figEnt = tk.Entry(row,textvariable=self.figsettings["figsize"])
        self.figEnt.pack(side=tk.RIGHT, expand=tk.YES, fill=tk.X)

        row = tk.Frame(settingsWindow)
        row.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        lab = tk.Label(row, width=25, text="font size", anchor='w')
        lab.pack(side=tk.LEFT)
        self.figEnt = tk.Entry(row,textvariable=self.figsettings["fontsize"])
        self.figEnt.pack(side=tk.RIGHT, expand=tk.YES, fill=tk.X)
        
        row = tk.Frame(settingsWindow)
        row.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        lab = tk.Label(row, width=25, text="fig. labels:", anchor='w')
        lab.pack(side=tk.LEFT)

        row = tk.Frame(settingsWindow)
        row.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        lab = tk.Label(row, width=25, text="\ttitle:", anchor='w')
        lab.pack(side=tk.LEFT)
        tk.Radiobutton(row,text="on", variable=self.figsettings["figtitle"], value=True).pack(side="left")
        tk.Radiobutton(row,text="off", variable=self.figsettings["figtitle"], value=False).pack(side="left")

        row = tk.Frame(settingsWindow)
        row.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        lab = tk.Label(row, width=25, text="\tx-axis:", anchor='w')
        lab.pack(side=tk.LEFT)
        tk.Radiobutton(row,text="on", variable=self.figsettings["figxaxis"], value=True).pack(side="left")
        tk.Radiobutton(row,text="off", variable=self.figsettings["figxaxis"], value=False).pack(side="left")

        row = tk.Frame(settingsWindow)
        row.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        lab = tk.Label(row, width=25, text="\ty-axis:", anchor='w')
        lab.pack(side=tk.LEFT)
        tk.Radiobutton(row,text="on", variable=self.figsettings["figyaxis"], value=True).pack(side="left")
        tk.Radiobutton(row,text="off", variable=self.figsettings["figyaxis"], value=False).pack(side="left")

        row = tk.Frame(settingsWindow)
        row.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        lab = tk.Label(row, width=25, text="export fig. vertical clip factor:", anchor='w')
        lab.pack(side=tk.LEFT)
        self.figEnt = tk.Entry(row,textvariable=self.figsettings["figclip"])
        self.figEnt.pack(side=tk.RIGHT, expand=tk.YES, fill=tk.X)

        row = tk.Frame(settingsWindow)
        row.pack(side=tk.TOP, anchor='c')
        b1 = tk.Button(row, text='save',
                    command=self.updateSettings)
        b1.pack(side="left")
        b2 = tk.Button(row, text='close', command=settingsWindow.destroy)
        b2.pack(side="left")


    def updateSettings(self):
        try:
            float(self.epsEnt.get())
            self.eps_r.set(self.epsEnt.get())
        except:
            self.eps_r.set(3.15)

        # make sure fig size is of correct format
        size = self.figsettings["figsize"].get().split(",")
        if len(size) != 2:
            self.figsettings["figsize"].set("6.5,1.5")
        try:
            float(size[0])
            float(size[1])
        except:
            self.figsettings["figsize"].set("6.5,1.5")

        # make sure font and vertical clip are floats
        try:
            self.figsettings["fontsize"].get()
        except:
            self.figsettings["fontsize"].set(12)
        try:
            self.figsettings["figclip"].get()
            val = self.figsettings["figclip"].get()
            if (val < 0) or (val > 1):
                self.figsettings["figclip"].set(1.0)
        except:
            self.figsettings["figclip"].set(1.0)

        # update impick figure settings
        self.impick.update_figsettings(self.figsettings)

        # pass updated dielectric to impick
        self.impick.set_eps_r(self.eps_r.get())
        self.impick.set_axes()

        # pass updated debug state to impick
        self.impick.set_debugState(self.debugState.get())

        # draw images
        self.impick.drawData()


    def help(self):
        # help message box
        helpWindow = tk.Toplevel(self.parent)
        helpWindow.title("instructions")
        helpWindow.config(bg="#d9d9d9")
        S = tk.Scrollbar(helpWindow)
        T = tk.Text(helpWindow, height=32, width=64, bg="#d9d9d9")
        S.pack(side=tk.RIGHT, fill=tk.Y)
        T.pack(side=tk.LEFT, fill=tk.Y)
        S.config(command=T.yview)
        T.config(yscrollcommand=S.set)
        note = """---Radar Analysis Graphical Utility---
        \n\n1.\tfile->open->data file: load data file
        \n2.\tfile->open->basemap file: load basemap
        \n3.\tpick->surface/subsurface->new: begin new pick segment 
        \n4.\t[spacebar]: toggle between radar and clutter images
        \n5.\tclick along reflector surface to pick horizon
        \n\t\u2022[backspace]: remove last pick
        \n\t\u2022[c]: remove all subsurface picks
        \n6.\tpick->surface/subsurface->stop: end current pick segment
        \n7.\t[spacebar]: toggle between radar and clutter images
        \n8.\tfile->save->picks: export picks
        \n9.\tfile->next: load next data file
        \n10.\tfile->quit: texit application"""
        T.insert(tk.END, note)


    def shortcuts(self):
        # shortcut info
        shortcutWindow = tk.Toplevel(self.parent)
        shortcutWindow.title("keyboard shortcuts")
        shortcutWindow.config(bg="#d9d9d9")
        S = tk.Scrollbar(shortcutWindow)
        T = tk.Text(shortcutWindow, height=32, width=64, bg="#d9d9d9")
        S.pack(side=tk.RIGHT, fill=tk.Y)
        T.pack(side=tk.LEFT, fill=tk.Y)
        S.config(command=T.yview)
        T.config(yscrollcommand=S.set)
        note = """---general---
                \n[ctrl+o]\t\t\topen data file
                \n[ctrl+m]\t\t\topen basemap
                \n[ctrl+s]\t\t\tsave picks
                \n[ctrl+q]\t\t\texit RAGU
                \n\n---profile view---
                \n[spacebar]\t\t\ttoggle between radar/clutter
                \n[h]\t\t\treturn to home extent
                \n[a]\t\t\tpan left
                \n[d]\t\t\tpan right
                \n[w]\t\t\tpan up
                \n[s]\t\t\tpan down
                \n[right]\t\t\topen next file in working directory
                \n---picking---
                \n[ctrl+n]\t\t\tbegin new subsurface pick segment
                \n[ctrl+shift+n]\t\t\tbegin new surface pick segment
                \n[escape]\t\t\tend current surface/subsurface\n\t\t\tpick segment
                \n[backspace]\t\t\tremove last pick event
                \n[c]\t\t\tremove all subsurface picks
                \n\n---waveform view---
                \n[h]\t\t\treturn to home extent
                \n[right]\t\t\tstep forward left
                \n[left]\t\t\tstep backward"""
        T.insert(tk.END, note)