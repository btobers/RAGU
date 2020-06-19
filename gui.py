"""
NOSEpick - Nearly Optimal Subsurface Extractor
created by: Brandon S. Tober and Michael S. Christoffersen
date: 25JUN19
last updated: 05FEB20
environment requirements in nose_env.yml
"""

### IMPORTS ###
# import ingester
import imPick, wvPick, basemap, utils, ingester
import os, sys, scipy, glob
import numpy as np
import matplotlib as mpl
mpl.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import tkinter as tk
import tkinter.ttk as ttk

# MainGUI is the NOSEpick class which sets the gui interface and holds operating variables
class MainGUI(tk.Frame):
    def __init__(self, parent, in_path, map_path, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)
        self.parent = parent
        self.in_path = in_path
        self.home_dir = in_path
        self.map_path = map_path
        self.setup()


    # setup is a method which generates the app menubar and buttons and initializes some vars
    def setup(self):
        self.f_loadName = ""
        self.f_saveName = ""
        self.map_loadName = ""

        self.userName = tk.StringVar(value="btober")
        self.eps = tk.DoubleVar(value=3.15)
        self.figSize = tk.StringVar(value="21,7")
        self.debugState = tk.BooleanVar()
        self.debugState.set(False)

        # generate menubar
        menubar = tk.Menu(self.parent)

        # create individual menubar items
        fileMenu = tk.Menu(menubar, tearoff=0)
        pickMenu = tk.Menu(menubar, tearoff=0)
        mapMenu = tk.Menu(menubar, tearoff=0)
        helpMenu = tk.Menu(menubar, tearoff=0)

        # file menu items
        fileMenu.add_command(label="open       [ctrl+o]", command=self.open_data)
        fileMenu.add_command(label="save       [ctrl+s]", command=self.save_loc)
        fileMenu.add_command(label="next        [right]", command=self.next_loc)

        # settings submenu
        settingsMenu = tk.Menu(fileMenu,tearoff=0)
        settingsMenu.add_command(label="preferences", command=self.settings)
        settingsMenu.add_command(label="set working directory", command=self.set_home)

        fileMenu.add_cascade(label="settings", menu = settingsMenu)

        fileMenu.add_command(label="exit       [ctrl+q]", command=self.close_window)

        # pick menu subitems
        surfacePickMenu = tk.Menu(pickMenu,tearoff=0)
        subsurfacePickMenu = tk.Menu(pickMenu,tearoff=0)

        # subsurface pick menu items
        subsurfacePickMenu.add_command(label="new     [ctrl+n]", command=self.start_subsurf_pick)
        subsurfacePickMenu.add_command(label="stop    [escape]", command=self.end_subsurf_pick)
        subsurfacePickMenu.add_command(label="clear        [c]", command=lambda: self.clear(surf = "subsurface"))    
        subsurfacePickMenu.add_command(label="clear file", command=self.delete_datafilePicks)            

        # surface pick menu items
        surfacePickMenu.add_command(label="new  [ctrl+shift+n]", command=self.start_surf_pick)
        surfacePickMenu.add_command(label="stop       [escape]", command=self.end_surf_pick)    
        surfacePickMenu.add_command(label="clear", command=lambda: self.clear(surf = "surface"))    

        pickMenu.add_cascade(label="surface", menu = surfacePickMenu)
        pickMenu.add_cascade(label="subsurface", menu = subsurfacePickMenu)  

        # pickMenu.add_separator()
        # pickMenu.add_command(label="Optimize", command=self.nb.select(wav))

        # map menu items
        mapMenu.add_command(label="open     [Ctrl+M]", command=self.map_loc)

        # help menu items
        helpMenu.add_command(label="instructions", command=self.help)
        helpMenu.add_command(label="keyboard shortcuts", command=self.shortcuts)

        # add items to menubar
        menubar.add_cascade(label="file", menu=fileMenu)
        menubar.add_cascade(label="pick", menu=pickMenu)
        menubar.add_cascade(label="map", menu=mapMenu)
        menubar.add_cascade(label="help", menu=helpMenu)
        
        # add the menubar to the window
        self.parent.config(menu=menubar)

        #configure imPick and wvPick tabs
        self.nb = ttk.Notebook(self.parent)
        self.nb.pack(side="top",anchor='w', fill="both", expand=1)
        self.imTab = tk.Frame(self.parent)
        self.imTab.pack()
        self.nb.add(self.imTab, text='imagePick')
        self.wvTab = tk.Frame(self.parent)
        self.wvTab.pack()
        self.nb.add(self.wvTab, text='wavePick')

        # bind tab change event to send pick data to wvPick if tab switched from imPick
        self.nb.bind("<<NotebookTabChanged>>", self.tab_change)

        # initialize imPick
        self.imPick = imPick.imPick(self.imTab)
        self.imPick.set_vars()

        # initialize wvPick
        self.wvPick = wvPick.wvPick(self.wvTab)
        self.wvPick.set_vars()

        # bind keypress events
        self.parent.bind("<Key>", self.key)

        # handle x-button closing of window
        self.parent.protocol("WM_DELETE_WINDOW", self.close_window)

        # self.set_home()
        self.open_data()


    # key is a method to handle UI keypress events
    def key(self,event):
        # event.state & 4 True for Ctrl+Key
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
            if self.tab == "imagePick":
                self.start_subsurf_pick()

        # Ctrl+Shift+N begin surface pick
        elif event.state & 5 == 5 and event.keysym == "N":
            if self.tab == "imagePick":
                self.start_surf_pick()

        # Ctrl+Q close NOSEpick
        elif event.state & 4 and event.keysym == "q":
            self.close_window()

        elif event.keysym =="Left":
            if self.tab == "wavePick":
                self.wvPick.stepBackward()

        # shift+. (>) next file
        elif event.keysym =="Right":
            if self.tab == "imagePick":
                self.next_loc()
            elif self.tab == "wavePick":
                self.wvPick.stepForward()


        # Escape key to stop picking current layer
        elif event.keysym == "Escape":
            if self.tab == "imagePick":
                self.end_subsurf_pick()
                self.end_surf_pick()

        # c key to clear all picks in imPick
        if event.keysym =="c":
            # clear the drawing of line segments
            self.clear(surf = "subsurface")
            
        # BackSpace to clear last pick 
        elif event.keysym =="BackSpace":
            if self.tab == "imagePick":
                self.imPick.clear_last()

        # Space key to toggle imPick between radar image and clutter
        elif event.keysym=="space":
            if self.tab == "imagePick":
                self.imPick.set_im()

        # h key to set axes limits to home extent
        elif event.keysym=="h":
            self.imPick.set_axes(self.eps.get())

    # close_window is a gui method to exit NOSEpick
    def close_window(self):
        # check if picks have been made and saved
        if ((self.imPick.get_subsurfPickFlag() == True) or (self.imPick.get_surfPickFlag == True)) and (self.f_saveName == ""):
            if tk.messagebox.askokcancel("Warning", "exit NOSEpick without saving picks?", icon = "warning") == True:
                self.parent.destroy()
        else:
            self.parent.destroy()


    # set_home is a method to set the session home directory
    def set_home(self):
        self.home_dir = tk.filedialog.askdirectory(title="root directory",
                                       initialdir=self.home_dir,
                                       mustexist=True)


    # open_data is a gui method which has the user select and input data file - then passed to imPick.load()
    def open_data(self):
        # select input file
        temp_loadName = tk.filedialog.askopenfilename(initialdir = self.home_dir,title = "select file",filetypes = (("all files",".*"),("hd5f files", ".mat .h5"),("segy files", ".sgy"),("image file", ".img")))
        # if input selected, clear imPick canvas, ingest data and pass to imPick
        if temp_loadName:
            self.f_loadName = temp_loadName
            self.imPick.clear_canvas()  
            self.imPick.set_vars()
            self.imPick.update_option_menu()
            # ingest the data
            self.igst = ingester.ingester(self.f_loadName.split(".")[-1])
            self.data = self.igst.read(self.f_loadName)

            # check for file errors
            if np.any(self.data["dist"]):
                self.imPick.load(self.f_loadName, self.data)
                self.imPick.set_axes(self.eps.get())
                self.imPick.update_bg()
                self.wvPick.set_vars()
                self.wvPick.clear()
                self.wvPick.set_data(self.data)
            
            else: 
                print("data file error, trying another!")
                self.open_data()

        # pass basemap to imPick for plotting pick location
        if self.map_loadName and self.basemap.get_state() == 1:
            self.basemap.clear_nav()
            self.basemap.set_nav(self.data["navdat"], self.f_loadName)
            self.imPick.get_basemap(self.basemap)            


    # save_loc is method to receieve the desired pick save location from user input
    def save_loc(self):
        if (self.f_loadName) and ((self.imPick.get_subsurfPickFlag() == True) or (self.imPick.get_surfPickFlag() == True)):
            out_path = self.f_loadName[:-len("/".join(self.f_loadName.split("/")[-2:]))] + "picks"
            if self.f_loadName.endswith(".mat"):
                out_path = self.f_loadName[:-len("/".join(self.f_loadName.split("/")[-3:]))] + "picks"
            self.f_saveName = tk.filedialog.asksaveasfilename(initialfile = os.path.splitext(self.f_loadName.split("/")[-1])[0] + "_pk",
                                initialdir = out_path, title = "save picks",filetypes = (("comma-separated values","*.csv"),))
        if self.f_saveName:
            self.end_surf_pick()
            self.end_subsurf_pick()
            # get updated pick_dict from wvPick and pass back to imPick
            self.imPick.set_pickDict(self.wvPick.get_pickDict())
            self.imPick.save(self.f_saveName, self.eps.get(), self.figSize.get().split(","))
    

    # map_loc is a method to get the desired basemap location and initialize
    def map_loc(self):
        tmp_map_loadName = ""
        tmp_map_loadName = tk.filedialog.askopenfilename(initialdir = self.map_path, title = "select basemap file", filetypes = (("geotiff files","*.tif"),("all files","*.*")))
            
        if tmp_map_loadName:
            self.map_loadName = tmp_map_loadName
            self.basemap = basemap.basemap(self.parent, self.map_loadName)
            self.basemap.map()

            if self.f_loadName:
                # pass basemap to imPick for plotting pick location
                self.basemap.set_nav(self.data["navdat"], self.f_loadName)
                self.imPick.get_basemap(self.basemap)


    # start_subsurf_pick is a method which begins a new imPick pick layer
    def start_subsurf_pick(self):
        if self.f_loadName:
            # end surface picking if currently active
            self.end_surf_pick()
            self.imPick.set_pickState(True,surf="subsurface")
            self.imPick.pick_interp(surf = "subsurface")
            self.imPick.plot_picks(surf = "subsurface")
            # add pick annotations
            self.imPick.add_pickLabels()
            self.imPick.update_bg()
            self.imPick.blit()
            self.imPick.update_option_menu()


    # end_subsurf_pick is a method which terminates the current imPick pick layer
    def end_subsurf_pick(self):
        if (self.imPick.get_pickState() is True) and (self.imPick.get_pickSurf() == "subsurface"):
            self.imPick.set_pickState(False,surf="subsurface")
            self.imPick.pick_interp(surf = "subsurface")
            self.imPick.plot_picks(surf = "subsurface")
            # add pick annotations
            self.imPick.add_pickLabels()
            self.imPick.update_bg()
            self.imPick.blit()
            self.imPick.update_option_menu()


    # start picking the surface
    def start_surf_pick(self):
        if self.f_loadName:
            # end subsurface picking if currently active
            self.end_subsurf_pick()
            self.imPick.set_pickState(True,surf="surface")


    # end surface picking
    def end_surf_pick(self):
        if (self.imPick.get_pickState() is True) and (self.imPick.get_pickSurf() == "surface"):
            self.imPick.set_pickState(False,surf="surface")
            self.imPick.pick_interp(surf = "surface")
            self.imPick.plot_picks(surf = "surface")
            self.imPick.blit()


    # next_loc is a method to get the filename of the next data file in the directory then call imPick.load()
    def next_loc(self):
        if self.tab == "imagePick" and self.f_loadName and self.imPick.nextSave_warning() == True:
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
                self.imPick.clear_canvas()
                self.imPick.set_vars()
                self.imPick.update_option_menu()
                self.data = self.igst.read(self.f_loadName)
                self.imPick.load(self.f_loadName, self.data)
                self.imPick.set_axes(self.eps.get())
                self.imPick.update_bg()
                self.wvPick.clear()
                self.wvPick.set_vars()
                self.wvPick.set_data(self.data)

                # if basemap open, update. Only do this if line is longer than certain threshold to now waste time
                if self.map_loadName and self.basemap.get_state() == 1:
                    if self.data["dist"][-1] > 5:
                        self.basemap.clear_nav()
                        self.basemap.set_nav(self.data["navdat"], self.f_loadName)
                        self.imPick.get_basemap(self.basemap)

            else:
                print("Note: " + self.f_loadName.split("/")[-1] + " is the last file in " + file_path + "*." + self.f_loadName.split(".")[-1])


    def tab_change(self, event):
        selection = event.widget.select()
        self.tab = event.widget.tab(selection, "text")
        # determine which tab is active
        if (self.tab == "wavePick"):
            if self.f_loadName:
                self.pick_opt()
        elif (self.tab == "imagePick"):
            # get updated pick_dict and surf_idx from wvPick and pass back to imPick if dictionaries differ
            if (self.imPick.get_subsurfPickFlag() == True) and (self.dict_compare(self.imPick.get_pickDict(),self.wvPick.get_pickDict()) == False) and (tk.messagebox.askyesno("tab change","import optimized picks to imagePick from wavePick?") == True):
                self.imPick.set_pickDict(self.wvPick.get_pickDict())
                self.imPick.plot_picks(surf = "subsurface")
            elif (self.imPick.get_surfPickFlag() == True):
                self.imPick.plot_picks(surf = "surface")
            self.imPick.blit()


    # pick_opt is a method to load the wvPick optimization tools
    def pick_opt(self):
        # end any picking
        self.end_subsurf_pick()
        self.end_surf_pick()
        # get pick dict from imPick and pass to wvPick
        self.wvPick.set_pickDict(self.imPick.get_pickDict())
        self.wvPick.plot_wv()


    # dict_compare is a method to compare the subsurface pick dictionaries from wvPick and imPick to determine if updates have been made
    def dict_compare(self, dict_imPick, dict_wvPick):
        for _i in range(len(dict_imPick)):
            if not (np.array_equal(dict_imPick[str(_i)] ,dict_wvPick[str(_i)])):
                return False


    # clear is a method to clear all picks
    def clear(self, surf = None):
        if self.f_loadName:
            if (surf == "surface") and (tk.messagebox.askokcancel("warning", "clear all surface picks?", icon = "warning") == True):
                self.imPick.clear_picks(surf = "surface")
                self.imPick.plot_picks(surf = "surface")
                self.imPick.blit()
            elif (self.imPick.get_subsurfPickFlag() == True) and (surf == "subsurface") and (tk.messagebox.askokcancel("warning", "clear all subsurface picks?", icon = "warning") == True):
                self.imPick.clear_picks(surf = "subsurface")
                self.imPick.plot_picks(surf = "subsurface")
                self.imPick.update_bg()
                self.imPick.blit()
                self.imPick.update_option_menu()
                self.wvPick.set_vars()
                self.wvPick.clear()


    # delete_datafilePicks is a method to clear subsurface picks saved to the data file
    def delete_datafilePicks(self):
            if (self.data["num_file_pick_lyr"] > 0) and (tk.messagebox.askokcancel("warning", "delte data file subsurface picks?", icon = "warning") == True):
                self.imPick.remove_imported_picks()
                self.imPick.update_bg()
                self.imPick.blit()
                utils.delete_savedPicks(self.f_loadName, self.data["num_file_pick_lyr"])
                self.data["num_file_pick_lyr"] = 0


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
        self.epsEnt = tk.Entry(row,textvariable=self.eps)
        self.epsEnt.pack(side=tk.RIGHT, expand=tk.YES, fill=tk.X)

        row = tk.Frame(settingsWindow)
        row.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        lab = tk.Label(row, width=25, text="export fig. size [w,h]", anchor='w')
        lab.pack(side=tk.LEFT)
        self.figEnt = tk.Entry(row,textvariable=self.figSize)
        self.figEnt.pack(side=tk.RIGHT, expand=tk.YES, fill=tk.X)

        row = tk.Frame(settingsWindow)
        row.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        lab = tk.Label(row, width=25, text="degub mode", anchor='w')
        lab.pack(side=tk.LEFT)
        tk.Radiobutton(row,text="on", variable=self.debugState, value=True).pack(side="left")
        tk.Radiobutton(row,text="off", variable=self.debugState, value=False).pack(side="left")
        
        b1 = tk.Button(settingsWindow, text='save',
                    command=self.updateSettings)
        b1.pack(side=tk.LEFT, padx=5, pady=5)
        b2 = tk.Button(settingsWindow, text='close', command=settingsWindow.destroy)
        b2.pack(side=tk.LEFT, padx=5, pady=5)


    def updateSettings(self):
        self.userName.set(self.userEnt.get())
        self.figSize.set(self.figEnt.get())
        try:
            float(self.epsEnt.get())
            self.eps.set(self.epsEnt.get())
        except:
            self.eps.set(3.15)

        # make sure fig size is of correct format
        size = self.figSize.get().split(",")
        if len(size) != 2:
            self.figSize.set("21,7")
        try:
            float(size[0])
            float(size[1])
        except:
            self.figSize.set("21,7")
        
        # pass updated dielectric to imPick
        self.imPick.set_axes(self.eps.get())

        # pass updated debug state to imPick
        self.imPick.set_debugState(self.debugState.get())


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
        \n[ctrl+s]\texport pick data
        \n[→]\t\topen next file in\n\t\tworking directory
        \n[ctrl+q]\tquit NOSEpick
        \n\n---picking---
        \n[ctrl+n]\tbegin new subsurface pick\n\t\tsegment
        \n[ctrl+shift+n]\tbegin new surface pick\n\t\tsegment
        \n[escape]\tend current surface/\n\t\tsubsurface pick segment
        \n[backspace]\tremove last pick event
        \n[c]\t\tremove all picked\n\t\tsubsurface segments""")