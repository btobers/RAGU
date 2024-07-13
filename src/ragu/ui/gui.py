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
from ragu.raguError import raguError
from ragu.ui import impick, wvpick, basemap, notepad
from ragu.tools import utils, export
from ragu.ingest import ingest
import os, sys, scipy, glob, configparser, datetime, copy
import numpy as np
import pandas as pd
import matplotlib as mpl
mpl.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import tkinter as tk
import tkinter.ttk as ttk
# try:
#     plt.rcParams["font.family"] = "Times New Roman"
# except:
#     pass

class mainGUI(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
        tk.Frame.__init__(self, parent)
        self.parent = parent
        # read and parse config
        self.conf = configparser.ConfigParser()
        self.conf.read(kwargs['configPath'])
        if kwargs['datPath']:
            self.datPath = kwargs['datPath']
        else:
            self.datPath = self.conf["path"]["datPath"]
        # initialize variables
        self.rdata = None
        self.f_loadName = ""
        self.map_loadName = ""
        self.tab = "Profile"
        self.eps_r = tk.DoubleVar(value=self.conf["output"]["eps_r"])
        self.popup = popup(self.parent)
        self.proj = project()
        self.pick_vis = tk.BooleanVar()
        self.pick_vis.set(True)
        self.ann_vis = tk.BooleanVar()
        self.ann_vis.set(True)
        # dictionary to hold figure settings
        self.figsettings = {"cmap": tk.StringVar(value=self.conf["param"]["cmap"]),
                            "figsize": tk.StringVar(value="6.5,1.5"), 
                            "fontsize": tk.DoubleVar(value="10"),
                            "figtitle": tk.BooleanVar(),
                            "figxaxis": tk.BooleanVar(),
                            "figyaxis": tk.BooleanVar(),
                            "figclip": (tk.DoubleVar(value=0.0),tk.DoubleVar(value=1.0))}
        self.figsettings["figxaxis"].set(True)        
        self.figsettings["figyaxis"].set(True)        
        self.figsettings["figtitle"].set(True)        
        self.debugState = tk.BooleanVar()
        self.debugState.set(False)
        self.os = sys.platform
        # setup tkinter frame
        self.setup()
        # if passed, load datafile
        if kwargs['datFile']:
            self.open_dfile(kwargs['datFile'])


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
        # |  |  |-high pass
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
        interpretMenu = tk.Menu(menubar, tearoff=0)
        procMenu = tk.Menu(menubar, tearoff=0)
        viewMenu = tk.Menu(menubar, tearoff=0)
        helpMenu = tk.Menu(menubar, tearoff=0)

        ### file menu items ###
        # open submenu
        openMenu = tk.Menu(fileMenu,tearoff=0)
        openMenu.add_command(label="Project", command=self.open_proj)
        openMenu.add_command(label="Data File    [Ctrl+O]", command=self.choose_dfile)
        openMenu.add_command(label="Basemap  [Ctrl+M]", command=self.init_bm)
        openMenu.add_command(label="Notepad", command=self.init_notepad)

        fileMenu.add_cascade(label="Open", menu=openMenu)
        fileMenu.add_command(label="Last      [◀]", command=lambda:self.switch_dfile(direction="Left"))
        fileMenu.add_command(label="Next      [▶]", command=lambda:self.switch_dfile(direction="Right"))

        # export submenu
        exportMenu = tk.Menu(fileMenu,tearoff=0)
        exportMenu.add_command(label="Project", command=self.export_proj)
        datExportMenu = tk.Menu(exportMenu,tearoff=0)
        datExportMenu.add_command(label="Raw Amplitude", command=lambda:self.export_dat(type="raw"))
        datExportMenu.add_command(label="Processed Amplitude", command=lambda:self.export_dat(type="proc"))
        exportMenu.add_cascade(label="Radar Data", menu=datExportMenu)
        pickExportMenu = tk.Menu(exportMenu,tearoff=0)
        pickExportMenu.add_command(label="Horizon", command=self.export_pick)
        pickExportMenu.add_command(label="All Horizons", command=lambda:self.export_pick(flag="all"))
        pickExportMenu.add_command(label="Merged Horizons  [Ctrl+S]", command=lambda:self.export_pick(flag="merged"))
        exportMenu.add_cascade(label="Picks", menu=pickExportMenu)
        exportMenu.add_command(label="Figure", command=self.export_fig)
        exportMenu.add_command(label="Processing Script", command=self.export_log)
        fileMenu.add_cascade(label="Export", menu=exportMenu)
        fileMenu.add_separator()

        # settings submenu
        settingsMenu = tk.Menu(fileMenu,tearoff=0)
        settingsMenu.add_command(label="Preferences", command=self.settings)
        settingsMenu.add_command(label="Set Working Folder", command=self.set_home)
        settingsMenu.add_command(label="Set Output Folder", command=self.set_out)

        fileMenu.add_cascade(label="Settings", menu=settingsMenu)
        fileMenu.add_separator()
    
        fileMenu.add_command(label="Exit  [Ctrl+Q]", command=self.close_window)

        ### interpret menu items ###
        pickMenu = tk.Menu(interpretMenu,tearoff=0)
        pickMenu.add_command(label="Start       [Ctrl+N]", command=self.start_pick)
        pickMenu.add_command(label="Stop        [Escape]", command=self.end_pick)
        interpretMenu.add_cascade(label="Pick", menu=pickMenu)
        newMenu = tk.Menu(interpretMenu,tearoff=0)
        newMenu.add_command(label="Horizon", command=self.new_horizon)
        newMenu.add_command(label="Segment", command=self.new_segment)
        interpretMenu.add_cascade(label="New", menu=newMenu)
        editMenu = tk.Menu(interpretMenu,tearoff=0)
        editMenu.add_command(label="Segment", command=self.edit_pick)
        interpretMenu.add_cascade(label="Edit", menu=editMenu)
        rmMenu = tk.Menu(interpretMenu,tearoff=0)
        rmMenu.add_command(label="Horizon", command=lambda:self.clear_pick(hFlag=True))
        rmMenu.add_command(label="Segment", command=lambda:self.clear_pick(segFlag=True))
        rmMenu.add_command(label="All", command=lambda:self.clear_pick(allFlag=True))
        rmMenu.add_command(label="From File", command=self.delete_datafilePicks)
        interpretMenu.add_cascade(label="Remove", menu=rmMenu)
        interpretMenu.add_command(label="Import", command=self.import_pick)
        srfMenu = tk.Menu(interpretMenu,tearoff=0)
        srfMenu.add_command(label="Define Horizon", command=self.srf_define)
        srfMenu.add_command(label="Auto-pick", command=self.srf_autopick)
        interpretMenu.add_cascade(label="Surface", menu=srfMenu)        
        exportMenu = tk.Menu(interpretMenu,tearoff=0)
        exportMenu.add_command(label="Horizon", command=self.export_pick)
        exportMenu.add_command(label="All Horizons", command=lambda:self.export_pick(flag="all"))
        exportMenu.add_command(label="Merged Horizons  [Ctrl+S]", command=lambda:self.export_pick(flag="merged"))
        interpretMenu.add_cascade(label="Export", menu=exportMenu)

        ### processing menu items ###
        procMenu.add_command(label="Reverse Radargram", command=lambda:self.procTools("reverse"))
        procMenu.add_command(label="Set Time Zero", command=lambda:self.procTools("tzero"))
        procMenu.add_command(label="Flatten", command=lambda:self.procTools("flatten"))
        procMenu.add_command(label="Restack", command=lambda:self.procTools("restack"))
        procMenu.add_command(label="Vertical Data Roll", command=lambda:self.procTools("vroll"))
        # procMenu.add_command(label="Dewow", command=lambda:self.procTools("dewow"))

        # processing submenu items
        gainMenu = tk.Menu(procMenu,tearoff=0)

        # filtering related items
        procMenu.add_command(label="Background Removal", command=lambda:self.procTools("remSlidingMean"))
        procMenu.add_command(label="Filter", command=lambda:self.procTools("filter"))
        procMenu.add_command(label="Hilbert Xform", command=lambda:self.procTools("hilbert"))

        # gain submenu items
        # gainMenu.add_command(label="AGC", command=lambda:self.procTools("agc"))
        gainMenu.add_command(label="T-Pow", command=lambda:self.procTools("tpow"))
        procMenu.add_cascade(label="Gain", menu=gainMenu)

        procMenu.add_command(label="Undo [Ctrl+Z]", command=lambda:self.procTools("undo"))        
        procMenu.add_command(label="Reset", command=lambda:self.procTools("reset"))

        ### view menu items ###
        viewMenu.add_checkbutton(label="Interpretations", onvalue=True, offvalue=False, variable=self.pick_vis, command=self.set_pick_vis)
        viewMenu.add_checkbutton(label="Labels", onvalue=True, offvalue=False, variable=self.ann_vis, command=self.set_ann_vis)

        ### help menu items ###
        helpMenu.add_command(label="Instructions", command=self.help)
        helpMenu.add_command(label="Keyboard Shortcuts", command=self.shortcuts)

        # add items to menubar
        menubar.add_cascade(label="File", menu=fileMenu)
        menubar.add_cascade(label="Interpretation", menu=interpretMenu)
        menubar.add_cascade(label="Processing", menu=procMenu)
        menubar.add_cascade(label="View", menu=viewMenu)
        menubar.add_cascade(label="Help", menu=helpMenu)
        
        # add the menubar to the window
        self.parent.config(menu=menubar)

        # configure impick and wvpick tabs
        self.nb = ttk.Notebook(self.parent)
        self.nb.pack(side="top",anchor='w', fill="both", expand=1)
        self.imTab = tk.Frame(self.parent)
        self.imTab.pack()
        self.nb.add(self.imTab, text='Profile')
        self.wvTab = tk.Frame(self.parent)
        self.wvTab.pack()
        self.nb.add(self.wvTab, text='Waveform')

        # bind tab change event to send pick data to wvpick if tab switched from impick
        self.nb.bind("<<NotebookTabChanged>>", self.tab_change)

        # check cmap
        self.check_cmap()

        # initialize impick
        self.impick = impick.impick(self.imTab, button_tip, self.popup, self.figsettings["fontsize"].get())
        self.impick.set_vars()
        self.impick.update_figsettings(self.figsettings)
        self.impick.set_eps_r(self.eps_r.get())

        # initialize wvpick
        self.wvpick = wvpick.wvpick(self.wvTab, button_tip, self.reset_wvpick)
        self.wvpick.update_figsettings(self.figsettings)
        self.wvpick.set_vars()

        # initialize note
        self.notepad = notepad.notepad(parent=self.parent, init_dir=self.conf["path"]["outPath"])

        # set up  info frame
        infoFrame = tk.Frame(self.parent)
        infoFrame.pack(side="bottom",fill="x")
        self.rinfolbl = tk.Label(infoFrame)
        self.rinfolbl.pack(side="left")

        # handle x-button closing of window
        self.parent.protocol("WM_DELETE_WINDOW", self.close_window)

        # bind keypress events
        self.parent.bind("<Key>", self.key)


    # key is a method to handle UI keypress events
    def key(self,event):
        state = event.state
        key = event.keysym
        # event.state & 4 True for Ctrl+Key
        # event.state & 1 True for Shift+Key
        # general keps for either tab
        # Ctrl+O open file
        if state & 4 and key == "o":
            self.choose_dfile()

        # Ctrl+S save picks
        elif state & 4 and key == "s":
            self.export_pick(flag="merged")

        # Ctrl+M open map
        elif state & 4 and key == "m":
            self.init_bm()

        # Ctrl+Q close RAGU
        elif state & 4 and key == "q":
            self.close_window()

        # profile view keys
        if self.tab == "Profile":
            # Space key to toggle impick between radar image and sim
            if key =="space":
                self.impick.set_im(from_gui=True)

            elif state & 4 and key == "n":
                self.start_pick()

            # Escape key to stop picking current layer
            elif key == "Escape":
                self.end_pick()

            # BackSpace to clear last pick 
            elif key =="BackSpace":
                self.impick.clear_last()

            # c key to clear all picks in impick
            elif key =="c":
                # clear picks
                self.clear_pick(allFlag=True)

            # right key next file
            elif key =="Left" or key == "Right":
                self.switch_dfile(direction=key)

            # h key to set axes limits to home extent
            elif key =="h":
                self.impick.fullExtent()

            # plus key to zoom in
            elif key =="plus":
                self.impick.zoomIn()

            # minus key to zoom out
            elif key =="minus":
                self.impick.zoomOut()

            # d key to set axes limits to pan right
            elif key =="d":
                self.impick.panRight()

            # a key to set axes limits to pan left
            elif key =="a":
                self.impick.panLeft()

            # w key to set axes limits to pan up
            elif key =="w":
                self.impick.panUp()

            # s key to set axes limits to pan down
            elif  key=="s":
                self.impick.panDown()

            # Ctrl+z undo last processing
            elif state & 4 and key == "f":
                            self.procTools(arg="filter")

            # Ctrl+z undo last processing
            elif state & 4 and key == "z":
                            self.procTools(arg="undo")

            # Ctrl+z undo last processing
            elif state & 4 and key == "y":
                            self.procTools(arg="redo")

        # waveform view keys
        if self.tab == "Waveform":
            # h key to set axes limits to home extent
            if key =="h":
                self.wvpick.fullExtent()
    
            # a key to step back in trace count
            elif key =="Right":
                self.wvpick.stepForward()

            # d key to step forward in trace count
            elif key =="Left":
                self.wvpick.stepBackward()


    # save_check is a method to check if picks have been saved - a bit messy (need to account for potential "srf" ingested upon data load)
    def save_check(self):
        if self.rdata:
            # if horizons exist, but no output pick df
            if (self.rdata.pick.get_pick_flag()) and (self.rdata.out is None):
                horizons = list(self.rdata.pick.horizons.keys())
                # if srf is only horizon
                if "srf" in horizons and len(horizons) == 1:
                    # if srf was not ingested upon data load rdata.srfElev will be all nan
                    if np.isnan(self.rdata.srfElev).all():
                        return False
                    else:
                        return True
                # if non-srf horizons exist
                else:
                    return False
            # if no horizons exist or horizons already exported
            else:
                return True


    # close_window is a gui method to exit RAGU
    def close_window(self):
        # check if picks have been made and saved
        if self.save_check() == False:
            if tk.messagebox.askokcancel("Warning", "Exit RAGU without saving picks?", icon = "warning") == True:
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


    # open project
    def open_proj(self, proj_loadName=None):
        # save_check
        if (self.save_check() == False) and (tk.messagebox.askyesno("Warning", "Discard unsaved picks?", icon = "warning") == False):
            return

        # # if h5 file already open, save pick layer to data file
        # if (self.rdata) and (self.rdata.out is None) and (self.rdata.fpath.endswith(".h5")) and (self.rdata.dtype=="oibak"):
        #     export.h5(self.rdata.fpath, pd.DataFrame({"bed_twtt":np.repeat(np.nan, self.rdata.tnum)}), self.rdata.dtype)

        if proj_loadName is None:
            # select input file
            if self.os == "darwin":
                proj_loadName = tk.filedialog.askopenfilename(initialdir = self.conf["path"]["outPath"] + '/../', title = "select project file")
            else:
                proj_loadName = tk.filedialog.askopenfilename(initialdir = self.conf["path"]["outPath"] + '/../',title = "select project file",filetypes = [("ragu project", ".ragu"),
                                                                                                                            ("all files",".*")])
        
        if proj_loadName:
            try:
                self.proj.set_projPath(proj_loadName)
                self.proj.load()
                if self.proj.get_datPath():
                    self.open_dfile(self.proj.get_datPath())
                if self.proj.get_mapPath():
                    self.init_bm(self.proj.get_mapPath())
                if self.proj.get_notePath():
                    self.init_notepad(self.proj.get_notePath())
            except Exception as err:
                print("Load project error: {}".format(err))


    # choose_dfile is a gui method which has the user select and input data file - then passed to impick.load()
    def choose_dfile(self):
        # save_check
        if (self.save_check() == False) and (tk.messagebox.askyesno("Warning", "Discard unsaved picks?", icon = "warning") == False):
            return

        # # if h5 file already open, save pick layer to data file
        # if (self.rdata) and (self.rdata.out is None) and (self.rdata.fpath.endswith(".h5")) and (self.rdata.dtype=="oibak"):
        #     export.h5(self.rdata.fpath, pd.DataFrame({"bed_twtt":np.repeat(np.nan, self.rdata.tnum)}), self.rdata.dtype)

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

        if temp_loadName.endswith(".ragu"):
            self.open_proj(proj_loadName=temp_loadName)
        
        else:
            self.open_dfile(temp_loadName)


    # open_dat loads the data file and passes to other modules
    def open_dfile(self, f_loadName=None, switch=False, direction="Right"):
            # if input selected, clear impick canvas, ingest data and pass to impick
            try:
            # for fuck in ['bananas']:
                if f_loadName:
                    # switch to profile tab
                    if self.tab == "Waveform":
                        self.nb.select(self.nb.tabs()[0])
                    self.f_loadName = f_loadName
                    # update and save project file
                    self.proj.update_paths(self.f_loadName, self.map_loadName, self.notepad._notepad__get_file())
                    self.proj.save()
                    # ingest the data
                    self.igst = ingest(self.f_loadName)
                    self.rdata = self.igst.read(self.conf["path"]["simPath"], self.conf["nav"]["crs"], self.conf["nav"]["body"])
                    try:
                        self.rdata.asep =  float(self.conf["output"]["asep"])
                        self.rdata.info["Antenna Separation [m]"] = self.rdata.asep
                    except:
                        pass
                    self.impick.clear_canvas()  
                    self.impick.set_vars()
                    self.impick.load(self.rdata)
                    # set existing horizons
                    for horizon in self.rdata.pick.horizons.keys():
                        self.impick.set_picks(horizon=horizon)
                    self.impick.set_pickState(state=False)
                    self.impick.update_hor_opt_menu()
                    self.impick.update_seg_opt_menu
                    self.impick.set_axes()
                    self.impick.drawData()
                    self.impick.update_pickLabels()
                    self.impick.update_bg()
                    self.wvpick.set_vars()
                    self.wvpick.clear()
                    self.wvpick.set_data(self.rdata)
                    self.rinfolbl.config(text = '\t\t'.join('{}: {}'.format(k, d) for k, d in self.rdata.info.items()))

                # pass basemap to impick for plotting pick location
                if self.map_loadName and self.basemap.get_state() == 1:
                    self.basemap.set_track(self.rdata.fn)
                    self.basemap.set_nav(self.rdata.fn, self.rdata.navdf)
                    self.basemap.plot_tracks()
                    self.impick.get_basemap(self.basemap)
        
                if self.rdata and self.notepad._notepad__get_state() == 1:
                    self.notepad._notepad__write_track(fn=self.rdata.fn)
                    if self.notepad._notepad__get_file():
                        self.notepad._notepad__saveFile()

                # see if user would like  to load previous pick file
                tmpf = self.conf["path"]["outPath"] + self.rdata.fn + "_pk_" + self.conf["param"]["uid"] + ".csv"
                if (os.path.isfile(tmpf)) and (tk.messagebox.askyesno("Load Picks", "Load pick file: {}?".format(tmpf), icon = "question") == True):
                    self.import_pick(tmpf)


            # recall choose_dfile if wrong file type is selected 
            except Exception as err:
                # if switch, just advance to next file
                if switch:
                    self.switch_dfile(direction)
                else:
                    print(err)
                    self.choose_dfile() 


    # switch_dfile is a method to get the filename of the last/next data file in the directory to open
    def switch_dfile(self, direction="Right"):
        if self.tab == "Profile" and self.f_loadName:
            # prompt save check
            if (self.save_check() == False) and (tk.messagebox.askyesno("Warning", "Discard unsaved picks?", icon = "warning") == False):
                return

            # # if h5 file already open, save pick layer to data file
            # if (self.rdata) and (self.rdata.out is None) and (self.rdata.fpath.endswith(".h5")) and (self.rdata.dtype=="oibak"):
            #     export.h5(self.rdata.fpath, pd.DataFrame({"bed_twtt":np.repeat(np.nan, self.rdata.tnum)}), self.rdata.dtype)
            
            file_path = os.path.dirname(self.f_loadName)

            # get index of crurrently displayed file in directory
            file_list = [file_path + "/" + f for f in sorted(os.listdir(file_path)) if f.endswith(self.igst.ftype) or f.endswith(self.igst.ftype.upper())]
            file_index = file_list.index(self.f_loadName)

            if direction=="Right":
                # add one to index to load next file
                file_index += 1

                # check if more files exist in directory following current file
                if file_index <= (len(file_list) - 1):
                    self.open_dfile(file_list[file_index], True, direction)

                else:
                    print("Note: " + self.f_loadName.split("/")[-1] + " is the last file in " + file_path + "/*." + self.f_loadName.split(".")[-1])

            elif direction=="Left":
                # add one to index to load next file
                file_index -= 1

                # check if more files exist in directory following current file
                if file_index >= 0:
                    self.open_dfile(file_list[file_index], True, direction)

                else:
                    print("Note: " + self.f_loadName.split("/")[-1] + " is the first file in " + file_path + "/*." + self.f_loadName.split(".")[-1])
    

    # generate new interpretation horizon
    def new_horizon(self):
        if self.f_loadName:
            self.impick.init_horizon()


    # generate new interpretation segment for specified horizon
    def new_segment(self):
        if self.f_loadName:
            self.impick.init_segment()


    # start impick picking functionality
    def start_pick(self):
        if self.f_loadName:
            self.impick.set_pickState(True)


    # end impick picking functionality
    def end_pick(self):
        if self.f_loadName:
            self.impick.set_pickState(False)


    def edit_pick(self):
        if self.f_loadName:
            self.impick.edit_segment()


    def clear_pick(self, hFlag=None, segFlag=None, allFlag=None):
        if self.f_loadName:
            if hFlag:
                self.impick.rm_horizon()
            if segFlag:
                self.impick.rm_segment()
            if allFlag:
                self.impick.rm_horizon(rm_all=True)

    
    # import_pick is a method to load and plot picks saved to a csv file
    def import_pick(self, path=None):
        if self.f_loadName:
            if path:
                if os.path.isfile(path):
                    pk_file = path
                else:
                    pk_file = ""
            else:
                pk_file = ""
                pk_file = tk.filedialog.askopenfilename(initialdir = self.conf["path"]["outPath"], title = "load picks", filetypes = (("comma separated value", "*.csv"),))
            if pk_file:
                horizons = self.igst.import_pick(pk_file, self.conf["param"]["uid"])
                for horizon in horizons:
                    self.impick.set_picks(horizon=horizon)
                self.impick.blit()


    # srf_define
    def srf_define(self, srf=None):
        horizons = list(self.rdata.pick.horizons)
        for h in ["srf","surf","surface"]:
            if h in horizons:
                srf = h
                break

        if (srf is None) and (len(horizons) > 0):
            if self.popup.flag == 1:
                return
            horizon_colors = self.impick.get_horizon_colors()
            # create popup window to get new horizon name and interpreatation color
            hname =tk.StringVar()
            hname.set(horizons[-1])
            popup = self.popup.new(title="Surface Horizon")
            tk.Label(popup, text="Select surface horizon from which to reference subsurface interpretations:").pack(fill="both", expand=True)
            dropdown = tk.OptionMenu(popup, hname, *horizons)
            dropdown["menu"].delete(0, "end")
            dropdown.config(width=20)
            dropdown.pack(fill="none", expand=True)
            self.set_menu_color(menu=dropdown, horizon=hname, colors=horizon_colors)
            # trace change in self.color to self.set_menu_color
            trace = hname.trace("w", lambda *args, menu=dropdown, horizon=hname, colors=horizon_colors : self.set_menu_color(menu, horizon, colors))
            for key, val in horizon_colors.items():
                dropdown["menu"].add_command(label=key, foreground=val, activeforeground=val, command=tk._setit(hname, key))
            button = tk.Button(popup, text="OK", command=lambda:self.popup.close(flag=0), width=20).pack(side="left", fill="none", expand=True)
            button = tk.Button(popup, text="Cancel", command=lambda:[hname.set(""), self.popup.close(flag=-1)], width=20).pack(side="left", fill="none", expand=True)
            # wait for window to be closed
            self.parent.wait_window(popup)
            # remove the trace
            hname.trace_vdelete("w", trace)
            srf = hname.get()
            if (not srf) or (self.popup.flag == -1):
                return
        self.rdata.pick.set_srf(srf)
        self.rdata.set_srfElev()


    # srf_autopick
    def srf_autopick(self):
        srf = self.rdata.pick.get_srf()
        if srf is None:
            srf = "srf" 
        elif not tk.messagebox.askyesno("Warning","Surface horizon already exists. Overwrite with auto-pick surface?"):
            return

        self.rdata.pick.horizons[srf] = utils.get_srf(np.abs(self.rdata.dat), self.rdata.info["Signal Type"])
        self.srf_define(srf=srf)
        self.impick.set_picks(horizon=srf)
        self.impick.blit()


    # export_proj
    def export_proj(self):
        # select input file
        tmp = self.proj.get_projPath()
        if not tmp:
            if self.os == "darwin":
                tmp = tk.filedialog.asksaveasfilename(initialdir = self.conf["path"]["outPath"], title = "save project file")
            else:
                tmp = tk.filedialog.asksaveasfilename(initialdir = self.conf["path"]["outPath"], title = "save project file",filetypes = [("ragu project", ".ragu"),
                                                                                                                            ("all files",".*")])
        
        if tmp:
            fn, ext = os.path.splitext(tmp)

            try:
                self.proj.set_projPath(fn + ".ragu")
                self.proj.update_paths(self.f_loadName, self.map_loadName, self.notepad._notepad__get_file())
                self.proj.save()
                print("Project file saved successfully:\t{}".format(fn + ".ragu"))

            except Exception as err:
                print("Save project error: {}".format(err))

        return

    # export_pick is method to receieve the desired pick save location from user input
    def export_pick(self, flag=None):
        if self.f_loadName:
            # see if any picks have been made
            if  self.rdata.pick.get_pick_flag():
                # get directory path to save data
                dir_out = tk.filedialog.askdirectory(title = "Save Location",
                                                    initialdir = self.conf["path"]["outPath"],
                                                    mustexist = True)

                if not dir_out:
                    return

                # end any active picking
                self.end_pick()
                # sort horizons by mean twtt in array
                self.rdata.pick.horizons = utils.sort_array_dict(self.rdata.pick.horizons, self.rdata.pick.get_srf())
                # get horizon to export
                horizon = None
                horizons = list(self.rdata.pick.horizons)

                # if flag is none export single horizon
                if flag is None:
                    if self.popup.flag == 1:
                        return
                    horizon_colors = self.impick.get_horizon_colors()
                    # create popup window to get new horizon name and interpreatation color
                    hname =tk.StringVar()
                    hname.set(horizons[-1])
                    popup = self.popup.new(title="Export Horizon")
                    tk.Label(popup, text="Select horizon to export:").pack(fill="both", expand=True)
                    dropdown = tk.OptionMenu(popup, hname, *horizons)
                    dropdown["menu"].delete(0, "end")
                    dropdown.config(width=20)
                    dropdown.pack(fill="none", expand=True)
                    self.set_menu_color(menu=dropdown, horizon=hname, colors=horizon_colors)
                    # trace change in self.color to self.set_menu_color
                    trace = hname.trace("w", lambda *args, menu=dropdown, horizon=hname, colors=horizon_colors : self.set_menu_color(menu, horizon, colors))
                    for key, val in horizon_colors.items():
                        dropdown["menu"].add_command(label=key, foreground=val, activeforeground=val, command=tk._setit(hname, key))
                    button = tk.Button(popup, text="OK", command=lambda:self.popup.close(flag=0), width=20).pack(side="left", fill="none", expand=True)
                    button = tk.Button(popup, text="Cancel", command=lambda:[hname.set(""), self.popup.close(flag=-1)], width=20).pack(side="left", fill="none", expand=True)
                    # wait for window to be closed
                    self.parent.wait_window(popup)
                    # remove the trace
                    hname.trace_vdelete("w", trace)
                    horizon = hname.get()
                    if (not horizon) or (self.popup.flag == -1):
                        return
                    else:
                        fn_out = dir_out + "/" + self.rdata.fn + "_" + horizon + "_pk_" + self.conf["param"]["uid"]


                # elif flag is merged export, append outfile name with _pk_uid
                elif flag=="merged":
                    fn_out = dir_out + "/" + self.rdata.fn + "_pk_" + self.conf["param"]["uid"]
                    if self.rdata.pick.get_srf() is None:
                        self.srf_define()
                    # update srf_elev
                    if self.rdata.pick.get_srf():
                        self.rdata.set_srfElev()
    
                # export single or merged horizons
                if flag is None or flag=="merged":
                    # ensure surface horizon is defined
                    self.srf_define()
                    # set output dataframe
                    self.rdata.set_out(export.pick_math(self.rdata, self.eps_r.get(), self.conf["output"]["amp"], horizon=horizon, srf=self.rdata.pick.get_srf()))
                    if self.conf["output"].getboolean("csv"):
                        export.csv(fn_out + ".csv", self.rdata.out)
                    if self.conf["output"].getboolean("gpkg"):
                        export.gpkg(fn_out + ".gpkg", self.rdata.out, self.conf["nav"]["crs"])


                # if flag is all, export all horizons individually
                elif flag == "all":
                    for h in horizons:
                        fn_out = dir_out + "/" + self.rdata.fn + "_" + h + "_pk_" + self.conf["param"]["uid"]
                        # export picks for each horizon
                        self.rdata.set_out(export.pick_math(self.rdata, self.eps_r.get(), self.conf["output"]["amp"], horizon=h, srf=self.rdata.pick.get_srf()))
                        if self.conf["output"].getboolean("csv"):
                            export.csv(fn_out + ".csv", self.rdata.out)
                        if self.conf["output"].getboolean("gpkg"):
                            export.gpkg(fn_out + ".gpkg", self.rdata.out, self.conf["nav"]["crs"])
                        fn_out = dir_out + "/" + self.rdata.fn + "_pk_" + self.conf["param"]["uid"]
                        

                if self.conf["output"].getboolean("fig"):
                    self.impick.export_fig(fn_out + ".png")
                # export project if projpath exists
                if self.proj.get_projPath():
                    self.export_proj()


    # export_dat is a method to save processed radar data
    def export_dat(self, type="raw"):
        if self.f_loadName:
            tmp_fn_out = ""
            if self.os == "darwin":
                tmp_fn_out = tk.filedialog.asksaveasfilename(initialfile = os.path.splitext(self.f_loadName.split("/")[-1])[0] + "_" + type + "_amp.csv",
                                initialdir = self.conf["path"]["outPath"], title = "save processed data")
            else:
                tmp_fn_out = tk.filedialog.asksaveasfilename(initialfile = os.path.splitext(self.f_loadName.split("/")[-1])[0] + "_" + type + "_amp",
                                initialdir = self.conf["path"]["outPath"], title = "save processed data", filetypes = [("comma-separated values",".csv")])
            if tmp_fn_out:
                fn, ext = os.path.splitext(tmp_fn_out)

                if type == "raw":
                    export.dat(fn + ".csv", self.rdata.get_dat())
                elif type == "proc":
                    export.dat(fn + ".csv", self.rdata.proc.get_curr_amp())


    # export_log is a method to save the processing log
    def export_log(self):
        if self.f_loadName:
            tmp_fn_out = ""
            tmp_fn_out = tk.filedialog.asksaveasfilename(initialfile = os.path.splitext(self.f_loadName.split("/")[-1])[0] + ".py",
                            initialdir = self.conf["path"]["outPath"], title = "save processing script")

            if tmp_fn_out:
                fn, ext = os.path.splitext(tmp_fn_out)

                export.log(fn + ".py", self.rdata.hist)

    # export_fig is a method to export the radargram image
    def export_fig(self):
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

            self.impick.export_fig(fn + ".png")


    # init_notepad is a method to initialize the ragu notepad widget
    def init_notepad(self, path=""):
        if self.notepad._notepad__get_state() == 0:
            self.notepad._notepad__setup(path=path)
            if path:
                self.notepad._notepad__openFile()
            if self.rdata:
                self.notepad._notepad__write_track(self.rdata.fn)


    # init_bm is a method to get the desired basemap location and initialize
    def init_bm(self, path=None):
        if not path:
            path = ""
            if self.os == "darwin":
                path = tk.filedialog.askopenfilename(initialdir = self.conf["path"]["mapPath"], title = "select basemap file")

            else:
                path = tk.filedialog.askopenfilename(initialdir = self.conf["path"]["mapPath"], title = "select basemap file", filetypes = [("geotiff files","*.tif"),
                                                                                                                                                        ("all files","*.*")])
        if path:
            # initialize basemap if not currently open
            if not self.map_loadName or self.basemap.get_state() == 0:
                self.basemap = basemap.basemap(self.parent, self.datPath, self.conf["nav"]["crs"], self.conf["nav"]["body"], self.from_basemap)
            self.map_loadName = path
            self.proj.set_mapPath(self.map_loadName)
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
        self.open_dfile(path + _i)


    # reset_wvpick passes picks from impick to wvpick
    def reset_wvpick(self, force=False, check=False):
        if self.wvpick.get_horizon_paths() is None:
            force = True
        else:
            impaths = self.impick.get_horizon_paths()
            wvpaths = self.wvpick.get_horizon_paths()
            for h in impaths.keys():
                if h not in wvpaths.keys():
                    check = True
                    break
                for s in impaths[h].keys():
                    if s not in wvpaths[h].keys():
                        check = True
                        break
            if check and tk.messagebox.askyesno("Import","Import updated horizon interpretations?"):
                force = True
        if force:
            self.wvpick.set_data(self.rdata)
            self.wvpick.set_horizon_colors(self.impick.get_horizon_colors())
            self.wvpick.set_horizon_paths(self.impick.get_horizon_paths())
            self.wvpick.set_picks()
            self.wvpick.plot_wv()


    # set tkinter menu font colors to match color name
    def set_menu_color(self, menu=None, horizon=None, colors=None, *args):
        if not [x for x in (menu, colors) if x is None]:
            h = horizon.get()
            if h:
                c = colors[h]
                menu.config(foreground=c, activeforeground=c, highlightcolor=c)


    # change tabs between profile and waveform views
    def tab_change(self, event):
        selection = event.widget.select()
        tmp = event.widget.tab(selection, "text")
        # don't do anything unless different tab selected
        if (tmp != self.tab) and (self.rdata):
            self.tab = tmp
            # determine which tab is active
            if (self.tab == "Waveform"):
                self.end_pick()
                # reset_wavepick
                self.reset_wvpick()
            elif (self.tab == "Profile"):
                # get updated picks from wvpick and pass back to impick if they differ
                if not (utils.compare_horizon_paths(self.wvpick.get_horizon_paths(), self.impick.get_horizon_paths())) and \
                        (tk.messagebox.askyesno("Import","Import optimized horizon interpretations?")):
                    self.impick.set_horizon_paths(self.wvpick.get_horizon_paths())
                    self.impick.blit()


    # delete_datafilePicks is a method to clear subsurface picks saved to the data file
    def delete_datafilePicks(self):
            if self.f_loadName and tk.messagebox.askokcancel("Warning", "Delete any existing data file bed picks?", icon = "warning") == True:
                utils.delete_savedPicks(self.f_loadName)


    # processing tools
    def procTools(self, arg = None):
        if self.f_loadName:
            procFlag = None
            simFlag = None
            if arg == "reverse":
                self.rdata.reverse()
                self.impick.reverse()
                procFlag = True

            elif arg == "tzero":
                # set tzero should only be used for ground-based GPR data
                self.rdata.set_tzero()
                if self.rdata.flags.sampzero > 0:
                    srf = self.rdata.pick.get_srf()
                    if srf is None:
                        srf = "srf"

                    # define surface horizon name to set index to zeros
                    self.rdata.pick.horizons[srf] = np.zeros(self.rdata.tnum)
                    self.srf_define(srf=srf)

                    # apply sample shift to existing horizons and update picks
                    for h in self.rdata.pick.horizons:
                        if h != srf:
                            self.rdata.pick.horizons[h] -= self.rdata.flags.sampzero
                    
                    # clear horizons from canvas and redraw shifted horizons
                    tmp = copy.deepcopy(self.rdata.pick.horizons)
                    self.impick.rm_horizon(rm_all=True, verify=False)
                    for h in tmp.keys():
                        self.rdata.pick.horizons[h] = tmp[h]
                        self.impick.set_picks(h)

                    self.impick.blit()
                    procFlag = True

            elif arg == "flatten":
                # if a surface is defined and data isn't already time-zero shifted, flatten

                if (self.rdata.pick.get_srf()) and (self.rdata.flags.sampzero == 0):
                    self.rdata.flatten()

                    # apply sample shift to existing horizons and update picks
                    # first copy horizons and remove them from impick cancas
                    tmp = copy.deepcopy(self.rdata.pick.horizons)
                    self.impick.rm_horizon(rm_all=True, verify=False)
                    for h in tmp:
                        self.rdata.pick.horizons[h] = tmp[h] - self.rdata.flags.sampzero
                        self.impick.set_picks(horizon=h)

                    self.impick.blit()
                    procFlag = True

            elif arg == "vroll":
                samples = tk.simpledialog.askinteger("input","number of samples to roll data array")
                self.rdata.vertical_roll(samples)
                procFlag = True

            elif arg == "restack":
                thold = tk.simpledialog.askfloat("input","GPS drift threshold between consecutive traces (m)", initialvalue=0.5)
                dist = tk.simpledialog.askfloat("input","restacking distance (m)", initialvalue=0)
                self.rdata.restack(dist, thold)
                procFlag = True

            elif arg == "dewow":
                print("dewow currently in development")
                # window = tk.simpledialog.askfloat("input","dewow window size (# samples/" +  str(int(self.rdata.snum)) + ")?")
                # proc = processing.dewow(self.rdata.dat, window=10)
                # procFlag = True

            elif arg == "hilbert":
                print("hilbert transform currently in development")
                # self.rdata.hilbertxform()
                # procFlag = True

            elif arg == "filter":
                if self.popup.flag == 1:
                    return
                # create popup window to get filter cutoff and direction
                popup = self.popup.new(title="Butterworth Filter")

                def cutoffentry(*args):
                    if btype.get() == "lowpass":
                        lowcut_ent.config(state="disabled")
                        highcut_ent.config(state="normal")
                    elif btype.get() == "highpass":
                        lowcut_ent.config(state="normal")
                        highcut_ent.config(state="disabled")
                    elif btype.get() == "bandpass":
                        lowcut_ent.config(state="normal")
                        highcut_ent.config(state="normal")

                row = tk.Frame(popup)
                row.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
                tk.Label(row, text="Filter Type: ").pack(side="left")
                btype = tk.StringVar()
                radio = tk.Radiobutton(row,text="Lowpass", variable=btype, value="lowpass")
                radio.pack(side="left")
                button_tip(self.parent, radio, "Pass all frequencies below the highcut frequency")

                radio = tk.Radiobutton(row,text="Highpass", variable=btype, value="highpass")
                radio.pack(side="left")
                button_tip(self.parent, radio, "Pass all frequencies above the lowcut frequency")

                radio = tk.Radiobutton(row,text="Bandpass", variable=btype, value="bandpass")
                radio.pack(side="left")
                button_tip(self.parent, radio, "Pass all frequencies above the lowcut frequency and below the highcut frequency")

                row = tk.Frame(popup)
                row.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
                tk.Label(row, text="Filter Direction: ").pack(side="left")
                direction = tk.IntVar(value=0)
                radio = tk.Radiobutton(row,text="Fast-Time", variable=direction, value=0)
                radio.pack(side="left")
                button_tip(self.parent, radio, "Filter in the fast-time direction (along-trace)")

                radio = tk.Radiobutton(row,text="Slow-Time", variable=direction, value=1)
                radio.pack(side="left")
                button_tip(self.parent, radio, "Filter in the slow-time direction (along-track)")
            
                row = tk.Frame(popup)
                row.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
                tk.Label(row, text="Lowcut Frequency: ").pack(side="left")
                lowcut = tk.StringVar()
                lowcut_ent = tk.Entry(row, textvariable=lowcut, width = 10)
                lowcut_ent.pack(side="left")
                lowcut_ent.delete(0, 'end')
                lowcut_ent.config(state="disabled")
                button_tip(self.parent, lowcut_ent, "Lower frequency bound")
                tk.Label(row, text="\tHighcut Frequency: ").pack(side="left")
                highcut = tk.StringVar()
                highcut_ent = tk.Entry(row, textvariable=highcut, width = 10)
                highcut_ent.pack(side="left")
                highcut_ent.delete(0, 'end')
                button_tip(self.parent, highcut_ent, "Upper frequency bound")

                row = tk.Frame(popup)
                row.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
                tk.Label(row, text="Order: ").pack(side="left")
                order = tk.IntVar(value=5)
                ent = tk.Entry(row, textvariable=order, width = 10)
                ent.pack(side="left")
                button_tip(self.parent, ent, "Butterworth filter order")

                row = tk.Frame(popup)
                row.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
                tk.Button(row, text="OK", command=lambda:self.popup.close(flag=0), width=10).pack(side="left", fill="none", expand=True)
                tk.Button(row, text="Cancel", command=lambda:self.popup.close(flag=-1), width=10).pack(side="left", fill="none", expand=True)

                btype.trace("w",cutoffentry)
                btype.set("lowpass")

                # wait for window to be closed
                self.parent.wait_window(popup)
                if self.popup.flag == -1:
                    return
                try:
                    if lowcut.get():
                        lowcut = float(lowcut.get())
                    else:
                        lowcut = None
                    if highcut.get():
                        highcut = float(highcut.get())
                    else:
                        highcut = None
                    if lowcut is None and highcut is None:
                        raise ValueError("Filter error: no lowcut or highcut frequencies specified.")
                    self.rdata.filter(btype=btype.get(), lowcut=lowcut, highcut=highcut, order=order.get(), direction=direction.get())
                    procFlag = True
                except Exception as err:
                    print(err)

            elif arg == "tpow":
                power = tk.simpledialog.askfloat("Input","Power for tpow gain?")
                self.rdata.tpowGain(power=power)
                procFlag = True

            elif arg == "remSlidingMean":
                window = tk.simpledialog.askinteger("Input","Window size for background removal (Number of Samples)?")
                if window <= self.rdata.tnum:
                    self.rdata.removeSlidingMeanFFT(window=window)
                    procFlag = True
                else:
                    raise raguError("Window size must not exceed the number of traces.")


            elif arg == "agc":
                print("automatic gain control currently in development")
                # window = tk.simpledialog.askfloat("input","AGC gain window size (# samples/" +  str(int(self.rdata.snum)) + ")?")
                # proc = processing.agcGain(self.rdata.dat, window=window)
                # procFlag = True

            elif arg == "undo":
                self.rdata.undo()
                procFlag = True

            elif arg == "redo":
                self.rdata.redo()
                procFlag = True

            elif arg == "reset":
                # reset origianl rdata
                self.rdata.reset()
                procFlag = True

            else:
                print("undefined processing method")
                exit(1)

            if procFlag:
                self.impick.set_crange()
                self.impick.drawData(force=True)
                self.wvpick.clear()
                self.wvpick.set_vars()
                self.wvpick.set_data(self.rdata)


    def settings(self):
        settingsWindow = tk.Toplevel(self.parent)

        row = tk.Frame(settingsWindow)
        row.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        label = tk.Label(row, text = "General")
        label.pack(side=tk.TOP)
        f = tk.font.Font(label, label.cget("font"))
        f.configure(underline=True)
        label.configure(font=f)

        row = tk.Frame(settingsWindow)
        row.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        lab = tk.Label(row, width=25, text="Dielectric constant", anchor='w')
        lab.pack(side=tk.LEFT)
        self.epsEnt = tk.Entry(row,textvariable=self.eps_r)
        self.epsEnt.pack(side=tk.RIGHT, expand=tk.YES, fill=tk.X)

        row = tk.Frame(settingsWindow)
        row.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        lab = tk.Label(row, width=25, text="Debug mode", anchor='w')
        lab.pack(side=tk.LEFT)
        tk.Radiobutton(row,text="On", variable=self.debugState, value=True).pack(side="left")
        tk.Radiobutton(row,text="Off", variable=self.debugState, value=False).pack(side="left")

        row = tk.Frame(settingsWindow)
        row.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        label = tk.Label(row, text = "Figure")
        label.pack(side=tk.TOP)
        f = tk.font.Font(label, label.cget("font"))
        f.configure(underline=True)
        label.configure(font=f)

        row = tk.Frame(settingsWindow)
        row.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        lab = tk.Label(row, width=25, text="Matplotlib color map", anchor='w')
        lab.pack(side=tk.LEFT)
        entry = tk.Entry(row,textvariable=self.figsettings["cmap"])
        entry.pack(side=tk.RIGHT, expand=tk.YES, fill=tk.X)
        button_tip(self.parent, entry, "Choose a matplotlib colormap. https://matplotlib.org/2.0.2/users/colormaps.html")


        row = tk.Frame(settingsWindow)
        row.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        lab = tk.Label(row, width=25, text='Figure size [w",h"]', anchor='w')
        lab.pack(side=tk.LEFT)
        entry = tk.Entry(row,textvariable=self.figsettings["figsize"])
        entry.pack(side=tk.RIGHT, expand=tk.YES, fill=tk.X)

        row = tk.Frame(settingsWindow)
        row.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        lab = tk.Label(row, width=25, text="Font size", anchor='w')
        lab.pack(side=tk.LEFT)
        entry = tk.Entry(row,textvariable=self.figsettings["fontsize"])
        entry.pack(side=tk.RIGHT, expand=tk.YES, fill=tk.X)
        
        row = tk.Frame(settingsWindow)
        row.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        lab = tk.Label(row, width=25, text="Labels:", anchor='w')
        lab.pack(side=tk.LEFT)

        row = tk.Frame(settingsWindow)
        row.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        lab = tk.Label(row, width=25, text="\tTitle:", anchor='w')
        lab.pack(side=tk.LEFT)
        tk.Radiobutton(row,text="On", variable=self.figsettings["figtitle"], value=True).pack(side="left")
        tk.Radiobutton(row,text="Off", variable=self.figsettings["figtitle"], value=False).pack(side="left")

        row = tk.Frame(settingsWindow)
        row.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        lab = tk.Label(row, width=25, text="\tX-axis:", anchor='w')
        lab.pack(side=tk.LEFT)
        tk.Radiobutton(row,text="On", variable=self.figsettings["figxaxis"], value=True).pack(side="left")
        tk.Radiobutton(row,text="Off", variable=self.figsettings["figxaxis"], value=False).pack(side="left")

        row = tk.Frame(settingsWindow)
        row.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        lab = tk.Label(row, width=25, text="\tY-axis:", anchor='w')
        lab.pack(side=tk.LEFT)
        tk.Radiobutton(row,text="On", variable=self.figsettings["figyaxis"], value=True).pack(side="left")
        tk.Radiobutton(row,text="Off", variable=self.figsettings["figyaxis"], value=False).pack(side="left")

        row = tk.Frame(settingsWindow)
        row.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        lab = tk.Label(row, width=25, text="Export figure vertical clip:", anchor='w')
        lab.pack(side=tk.LEFT)

        row = tk.Frame(settingsWindow)
        row.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        lab = tk.Label(row, width=25, text="\tTop:", anchor='w')
        lab.pack(side=tk.LEFT)
        entry = tk.Entry(row,textvariable=self.figsettings["figclip"][0])
        entry.pack(side=tk.RIGHT, expand=tk.YES, fill=tk.X)
        button_tip(self.parent, entry, "Top of figure vertical extent (Figure coordinates)")

        row = tk.Frame(settingsWindow)
        row.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        lab = tk.Label(row, width=25, text="\tBottom:", anchor='w')
        lab.pack(side=tk.LEFT)
        entry = tk.Entry(row,textvariable=self.figsettings["figclip"][1])
        entry.pack(side=tk.RIGHT, expand=tk.YES, fill=tk.X)
        button_tip(self.parent, entry, "Bottom of figure vertical extent (Figure coordinates)")

        row = tk.Frame(settingsWindow)
        row.pack(side=tk.TOP, anchor="c")
        b = tk.Button(row, text="Save", command=lambda:[self.updateSettings(), settingsWindow.destroy()])
        b.pack(side="left")


    def check_cmap(self):
        # check if cmap is recognized
        try:
            plt.get_cmap(self.figsettings["cmap"].get())
        except:
            self.figsettings["cmap"].set("seismic")


    def updateSettings(self):
        try:
            float(self.epsEnt.get())
            self.eps_r.set(self.epsEnt.get())
        except:
            self.eps_r.set(3.15)

        # check if cmap is recognized
        self.check_cmap()

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
            self.figsettings["fontsize"].set(10)

        # make sure figure extents are between 0 and 1
        try:
            self.figsettings["figclip"][0].get()
            self.figsettings["figclip"][1].get()
            
            top = self.figsettings["figclip"][0].get()
            bottom = self.figsettings["figclip"][1].get()
            if top < 0:
                self.figsettings["figclip"][0].set(0)
            if bottom > 1:
                self.figsettings["figclip"][1].set(1)
            if top > bottom:
                self.figsettings["figclip"][0].set(0)
        except:
            self.figsettings["figclip"][0].set(0)
            self.figsettings["figclip"][1].set(1)

        # update figure settings
        self.impick.update_figsettings(self.figsettings)
        self.wvpick.update_figsettings(self.figsettings)

        # pass updated dielectric to impick
        self.impick.set_eps_r(self.eps_r.get())
        self.impick.set_axes()

        # pass updated debug state to impick
        self.impick.set_debugState(self.debugState.get())

        # draw images
        self.impick.drawData()


    def set_pick_vis(self):
        self.impick.show_picks(vis=self.pick_vis.get())


    def set_ann_vis(self):
        self.impick.show_labels(vis=self.ann_vis.get())


    def help(self):
        # help message box
        helpWindow = tk.Toplevel(self.parent)
        helpWindow.title("Instructions")
        helpWindow.config(bg="#d9d9d9")
        S = tk.Scrollbar(helpWindow)
        T = tk.Text(helpWindow, height=32, width=64, bg="#d9d9d9")
        S.pack(side=tk.RIGHT, fill=tk.Y)
        T.pack(side=tk.LEFT, fill=tk.Y)
        S.config(command=T.yview)
        T.config(yscrollcommand=S.set)
        note = """---Radar Analysis Graphical Utility---
                \n\n1. File->Open->Data File:    Load data file
                \n2. File->Open->Basemap File:    Load basemap
                \n3. Interpretation->New->Horizon:    Initialize new horizon
                \n4. Interpretation->Start:    Start picking
                \n5. [Spacebar]:    Toggle between radar and clutter images
                \n6. Click along reflector surface to pick horizon
                \n    [Backspace]:    Remove last pick
                \n7. Interpretation->Stop:    Stop picking
                \n8. File->Save->Picks:    Export picks
                \n9. File->Next:    Load next data file
                \n10. File->Exit:    Exit RAGU"""
        T.insert(tk.END, note)


    def shortcuts(self):
        # shortcut info
        shortcutWindow = tk.Toplevel(self.parent)
        shortcutWindow.title("Keyboard Shortcuts")
        shortcutWindow.config(bg="#d9d9d9")
        S = tk.Scrollbar(shortcutWindow)
        T = tk.Text(shortcutWindow, height=32, width=64, bg="#d9d9d9")
        S.pack(side=tk.RIGHT, fill=tk.Y)
        T.pack(side=tk.LEFT, fill=tk.Y)
        S.config(command=T.yview)
        T.config(yscrollcommand=S.set)
        note = """---General---
                \n\n[Ctrl+O]\t\t\tOpen data file
                \n[Ctrl+M]\t\t\tOpen basemap
                \n[Ctrl+S]\t\t\tSave picks
                \n[Ctrl+Q]\t\t\tExit RAGU
                \n\n---Profile View---
                \n\n[Spacebar]\t\t\tToggle between radar/clutter
                \n[H]\t\t\tReturn to home extent
                \n[A]\t\t\tPan left
                \n[D]\t\t\tPan right
                \n[W]\t\t\tPan up
                \n[S]\t\t\tPan down
                \n[Right]\t\t\tOpen next file in working directory
                \n\n---Picking---
                \n\n[Ctrl+N]\t\t\tStart picking / initialize new segment
                \n[Escape/Doubleclick]\t\t\tStop picking
                \n[Backspace]\t\t\tRemove last pick
                \n[C]\t\t\tRemove all interpretations
                \n\n---Waveform View---
                \n\n[H]\t\t\tReturn to home extent
                \n[Right]\t\t\tStep forward left
                \n[Left]\t\t\tStep backward"""
        T.insert(tk.END, note)


class popup():
    # initialize popup window
    def __init__(self, parent=None):
        self.parent = parent
        self.flag = 0     # 0 == closed safely, 1 == open, -1 == closed unsafely

    # new
    def new(self, title="title", bg="#d9d9d9", geom="500x150"):
        self.popup = tk.Toplevel(self.parent)
        self.popup.geometry(geom)
        self.popup.config(bg=bg)
        self.popup.title(title)
        self.popup.protocol("WM_DELETE_WINDOW", lambda flag=-1 : self.close(flag))
        self.flag = 1
        return self.popup

    # close
    def close(self, flag=0):
        self.popup.destroy()
        self.flag = flag


class button_tip(object):
    """
    popup info on gui button
    """
    def __init__(self, parent, widget, text="widget info"):
        self.waittime = 500     # miliseconds
        self.wraplength = 180   # pixels
        self.parent = parent    # parent frame
        self.widget = widget
        self.text = text
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)
        self.widget.bind("<ButtonPress>", self.leave)
        self.id = None
        self.tw = None

    def enter(self, event=None):
        self.schedule()

    def leave(self, event=None):
        self.unschedule()
        self.hidetip()

    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(self.waittime, self.showtip)

    def unschedule(self):
        id = self.id
        self.id = None
        if id:
            self.widget.after_cancel(id)

    def showtip(self, event=None):
        try:
            self.parent.update()    # update parent to get size
            bounds = (self.parent.winfo_rootx(),(self.parent.winfo_rootx()+self.parent.winfo_width()))
            x = y = 0
            x, y, cx, cy = self.widget.bbox("insert")
            x += self.widget.winfo_rootx() + 25
            y += self.widget.winfo_rooty() + 25

            # creates a toplevel window
            self.tw = tk.Toplevel(self.widget)
            # Leaves only the label and removes the app window
            self.tw.wm_overrideredirect(True)
            self.tw.wm_geometry("+%d+%d" % (x, y))
            label = tk.Label(self.tw, text=self.text, justify='left',
                        background="#ffffff", relief='solid', borderwidth=1,
                        wraplength = self.wraplength)
            label.pack(ipadx=1)
            self.tw.update()

            # move tip window left if outside parent window bounds
            if (x + self.tw.winfo_width()) > bounds[1]:
                self.tw.wm_geometry("+%d+%d" % (x-self.tw.winfo_width(), y))
                self.tw.update()
        except:
            pass

    def hidetip(self):
        tw = self.tw
        self.tw= None
        if tw:
            tw.destroy()

    
class project():
    # handle current project
    def __init__(self):
        self.projPath = ""
        self.datPath = ""
        self.mapPath = ""
        self.notePath = ""

    def set_projPath(self, path=""):
        self.projPath = path

    def get_projPath(self):
        return self.projPath

    def set_datPath(self, path=""):
        self.datPath = path

    def get_datPath(self):
        return self.datPath

    def set_mapPath(self, path=""):
        self.mapPath = path

    def get_mapPath(self):
        return self.mapPath

    def set_notePath(self, path=""):
        self.notePath = path

    def get_notePath(self):
        return self.notePath

    def update_paths(self, datPath="", mapPath="", notePath=""):
        if datPath:
            self.datPath = datPath
        if mapPath:
            self.mapPath = mapPath
        if notePath:
            self.notePath = notePath
    
    def save(self):
        if self.projPath:
            file = open(self.projPath,"w") 
            file.write("[paths]\n") 
            file.write("datPath = {}\n".format(self.datPath)) 
            file.write("mapPath = {}\n".format(self.mapPath)) 
            file.write("notePath = {}\n".format(self.notePath)) 
            file.close() 

    def load(self):
        if self.projPath:
            # read and parse config
            conf = configparser.ConfigParser()
            conf.read(self.projPath)
            self.set_datPath(conf["paths"]["datPath"])
            self.set_mapPath(conf["paths"]["mapPath"])
            self.set_notePath(conf["paths"]["notePath"])