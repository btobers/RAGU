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
        mapMenu = tk.Menu(menubar, tearoff=0)
        helpMenu = tk.Menu(menubar, tearoff=0)

        # file menu items
        fileMenu.add_command(label="Open    [Ctrl+O]", command=self.open_data)
        fileMenu.add_command(label="Save    [Ctrl+S]", command=self.save_loc)
        fileMenu.add_command(label="Next     [Right]", command=self.next_loc)
        fileMenu.add_command(label="Exit    [Ctrl+Q]", command=self.close_window)

        # pick menu subitems
        surfacePickMenu = tk.Menu(pickMenu,tearoff=0)
        subsurfacePickMenu = tk.Menu(pickMenu,tearoff=0)

        # subsurface pick menu items
        subsurfacePickMenu.add_command(label="New     [Ctrl+N]", command=self.start_subsurf_pick)
        subsurfacePickMenu.add_command(label="Stop    [Escape]", command=self.end_subsurf_pick)

        # surface pick menu items
        surfacePickMenu.add_command(label="New", command=self.start_surf_pick)
        surfacePickMenu.add_command(label="Stop    [Escape]", command=self.end_surf_pick)    
        surfacePickMenu.add_command(label="Clear", command=lambda: self.clear(surf = "surface"))    

        pickMenu.add_cascade(label="Surface", menu = surfacePickMenu)
        pickMenu.add_cascade(label="Subsurface", menu = subsurfacePickMenu)  

        # pickMenu.add_separator()
        # pickMenu.add_command(label="Optimize", command=self.nb.select(wav))

        # map menu items
        mapMenu.add_command(label="Open     [Ctrl+M]", command=self.map_loc)

        # help menu items
        helpMenu.add_command(label="Instructions", command=self.help)
        helpMenu.add_command(label="Keyboard Shortcuts", command=self.shortcuts)

        # add items to menubar
        menubar.add_cascade(label="File", menu=fileMenu)
        menubar.add_cascade(label="Pick", menu=pickMenu)
        menubar.add_cascade(label="Map", menu=mapMenu)
        menubar.add_cascade(label="Help", menu=helpMenu)
        
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

        # Ctrl+N begin pick
        elif event.state & 4 and event.keysym == "n":
            if self.tab == "imagePick":
                self.start_subsurf_pick()

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


    # close_window is a gui method to exit NOSEpick
    def close_window(self):
        # check if picks have been made and saved
        if self.imPick.get_pickLen() > 0 and self.f_saveName == "":
            if tk.messagebox.askokcancel("Warning", "Exit NOSEpick without saving picks?", icon = "warning") == True:
                self.parent.destroy()
        else:
            self.parent.destroy()


    # open_data is a gui method which has the user select and input data file - then passed to imPick.load()
    def open_data(self):
        temp_loadName = ""
        # select input file
        temp_loadName = tk.filedialog.askopenfilename(initialdir = self.in_path,title = "Select file",filetypes = (("hd5f files", ".mat .h5"),("segy files", ".sgy"),("all files",".*")))
        # if input selected, clear imPick canvas, ingest data and pass to imPick
        if temp_loadName:
            self.f_loadName = temp_loadName
            self.imPick.clear_canvas()  
            self.imPick.set_vars()
            # ingest the data
            # try:
            self.igst = ingester.ingester(self.f_loadName.split(".")[-1])
            self.data = self.igst.read(self.f_loadName)
            self.imPick.load(self.f_loadName, self.data)
            self.wvPick.set_vars()
            self.wvPick.clear()
            self.wvPick.set_data(self.data)

            # except Exception as err:
            #     print('Ingest Error: ' + str(err))
            #     self.open_data()

        # pass basemap to imPick for plotting pick location
        if self.map_loadName and self.basemap.get_state() == 1:
            self.basemap.clear_nav()
            self.basemap.set_nav(self.data["navdat"], self.f_loadName)
            self.imPick.get_basemap(self.basemap)            


    # save_loc is method to receieve the desired pick save location from user input
    def save_loc(self):
        if self.f_loadName and self.imPick.get_pickLen() > 0:
            out_path = self.f_loadName[:-len("/".join(self.f_loadName.split("/")[-2:]))] + "picks"
            self.f_saveName = tk.filedialog.asksaveasfilename(initialfile = os.path.splitext(self.f_loadName.split("/")[-1])[0] + "_pk",
                                initialdir = out_path, title = "Save Picks",filetypes = (("comma-separated values","*.csv"),))
        if self.f_saveName:
            self.end_surf_pick()
            self.end_subsurf_pick()
            # get updated pick_dict from wvPick and pass back to imPick
            self.imPick.set_pickDict(self.wvPick.get_pickDict())
            self.imPick.save(self.f_saveName)
    

    # map_loc is a method to get the desired basemap location and initialize
    def map_loc(self):
        tmp_map_loadName = ""
        tmp_map_loadName = tk.filedialog.askopenfilename(initialdir = self.map_path, title = "Select basemap file", filetypes = (("GeoTIFF files","*.tif"),("all files","*.*")))
            
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
            self.imPick.blit()
            self.imPick.update_option_menu()


    # end_subsurf_pick is a method which terminates the current imPick pick layer
    def end_subsurf_pick(self):
        if (self.imPick.get_pickState() is True) and (self.imPick.get_pickSurf() == "subsurface"):
            self.imPick.set_pickState(False,surf="subsurface")
            self.imPick.pick_interp(surf = "subsurface")
            self.imPick.plot_picks(surf = "subsurface")
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
            # pass updated surface pick to wvPick
            self.wvPick.set_surf(self.data["twtt_surf"])


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
                self.data = self.igst.read(self.f_loadName)
                self.imPick.load(self.f_loadName, self.data)
                self.wvPick.clear()
                self.wvPick.set_vars()
                self.wvPick.set_data(self.data)


                if self.map_loadName and self.basemap.get_state() == 1:
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
            self.pick_opt()
        elif (self.tab == "imagePick"):
            # get updated pick_dict from wvPick and pass back to imPick if dictionaries differ
            if (self.imPick.get_pickLen() > 0) and (self.dict_compare(self.imPick.get_pickDict(),self.wvPick.get_pickDict()) == False) and (tk.messagebox.askokcancel("Tab Change","Import optimized picks to imagePick from wavePick?") == True):
                self.imPick.set_pickDict(self.wvPick.get_pickDict())
                self.imPick.plot_picks(surf = "subsurface")
                self.imPick.blit()


    # pick_opt is a method to load the wvPick optimization tools
    def pick_opt(self):
        # end any picking
        self.end_subsurf_pick()
        self.end_surf_pick()
        # get pick dict from imPick and pass to wvPick
        self.wvPick.set_pickDict(self.imPick.get_pickDict())
        self.wvPick.plot_wv()


    def dict_compare(self, dict_imPick, dict_wvPick):
        for _i in range(len(dict_imPick)):
            if not (np.array_equal(dict_imPick["segment_" + str(_i)] ,dict_wvPick["segment_" + str(_i)])):
                return False


    def clear(self, surf = None):
        if self.f_loadName:
            if (surf == "surface") and (tk.messagebox.askokcancel("Warning", "Clear all surface picks?", icon = "warning") == True):
                self.imPick.clear_picks(surf = "surface")
                self.imPick.plot_picks(surf = "surface")
                self.imPick.blit()
            elif (surf == "subsurface") and (tk.messagebox.askokcancel("Warning", "Clear all subsurface picks?", icon = "warning") == True):
                self.imPick.clear_picks(surf = "subsurface")
                self.imPick.plot_picks(surf = "subsurface")
                self.imPick.blit()
                self.imPick.update_option_menu()
                self.wvPick.set_vars()
                self.wvPick.clear()


    def help(self):
        # help message box
        tk.messagebox.showinfo("Instructions",
        """Nearly Optimal Subsurface Extractor:
        \n\n1. File->Load to load data file
        \n2. Map->Open to load basemap
        \n3. Pick->Surface/Subsurface->New to begin new pick segment 
        \n4. Click along reflector surface to pick\n   horizon
        \n\t\u2022[backspace] to remove the last
        \n\t\u2022[c] to remove all subsurface picks
        \n5. Pick->Surface/Subsurface->Stop to end current pick segment
        \n6. Radio buttons to toggle between radar\n   and clutter images
        \n7. File->Save to export picks
        \n8. File->Next to load next data file
        \n9. File->Quit to exit application""")


    def shortcuts(self):
        # shortcut list
        tk.messagebox.showinfo("Keyboard Shortcuts",
        """General:
        \n[Ctrl+o]\tOpen radar data file
        \n[Ctrl+m]\tOpen basemap window
        \n[Ctrl+n]\tBegin new subsurface pick segment
        \n[Escape]\tEnd current surface/subsurface pick segment
        \n[Spacebar]\tToggle between radar and clutter images
        \n[Ctrl+s]\tExport pick data
        \n[→]\t\tOpen next file in directory
        \n[Ctrl+q]\tQuit NOSEpick
        \n\nPicking:
        \n[Backspace]\tRemove last pick event
        \n[c]\t\tRemove all picked subsurface segments""")