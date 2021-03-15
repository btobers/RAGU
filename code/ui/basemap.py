# RAGU - Radar Analysis Graphical Utility
#
# copyright © 2020 btobers <tobers.brandon@gmail.com>
#
# distributed under terms of the GNU GPL3.0 license
"""
basemap class is a tkinter frame which handles the RAGU basemap
"""
### imports ###
from nav import navparse
from tools import utils
import numpy as np
import tkinter as tk
import rasterio as rio
import os, pyproj, glob
import matplotlib as mpl
mpl.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
try:
    plt.rcParams["font.family"] = "Times New Roman"
except:
    pass

class basemap(tk.Frame):
    def __init__(self, parent, datPath, navcrs, body, to_gui):
        self.parent = parent
        self.datPath = datPath
        self.navcrs = navcrs
        self.body = body
        self.to_gui = to_gui
        # create tkinter toplevel window to display basemap
        self.basemap_window = tk.Toplevel(self.parent)
        img = tk.PhotoImage(file="../recs/basemap_icon.png")
        self.basemap_window.tk.call("wm", "iconphoto", self.basemap_window._w, img)
        self.basemap_window.config(bg="#d9d9d9")
        self.basemap_window.title("RAGU - Map Window")
        self.map_display = tk.Frame(self.basemap_window)
        self.map_display.pack(side="bottom", fill="both", expand=1)
        # bind ctrl-q key to basemap_close()
        self.basemap_window.bind("<Control-q>", self.basemap_close)
        # bind x-out to basemap_close()
        self.basemap_window.protocol("WM_DELETE_WINDOW", self.basemap_close)
        self.cmap = tk.StringVar(value="Greys_r")
        self.setup()


    # setup the tkinter window
    def setup(self):
        # show basemap figure in basemap window
        # generate menubar
        menubar = tk.Menu(self.basemap_window)
        fileMenu = tk.Menu(menubar, tearoff=0)

        # settings submenu
        loadMenu = tk.Menu(fileMenu,tearoff=0)
        loadMenu.add_command(label="select files", command=self.load_tracks)
        loadMenu.add_command(label="select folder", command= lambda: self.load_tracks(dir = True))
        fileMenu.add_cascade(label="load tracks", menu = loadMenu)

        fileMenu.add_command(label="clear tracks", command=self.clear_nav)
        fileMenu.add_command(label="preferences", command=self.settings)
        fileMenu.add_command(label="exit       [ctrl+q]", command=self.basemap_close)
        # add items to menubar
        menubar.add_cascade(label="file", menu=fileMenu)
        # add the menubar to the window
        self.basemap_window.config(menu=menubar)

        # set up info frame
        infoFrame = tk.Frame(self.basemap_window)
        infoFrame.pack(side="top",fill="both")
        # button to toggle track visibility
        self.track_viz = tk.BooleanVar(value=True)
        tk.Label(infoFrame, text="track display: ").pack(side="left")
        tk.Radiobutton(infoFrame,text="all", variable=self.track_viz, value=True, command=self.plot_tracks).pack(side="left")
        tk.Radiobutton(infoFrame,text="current", variable=self.track_viz, value=False, command=self.plot_tracks).pack(side="left")

        # initialize the basemap figure
        self.map_fig = mpl.figure.Figure()
        self.map_fig.patch.set_facecolor(self.parent.cget("bg"))
        self.map_fig_ax = self.map_fig.add_subplot(111)
        self.bm_im = self.map_fig_ax.imshow(np.ones((100,100)), cmap=self.cmap.get(), aspect="auto")
        self.map_fig_ax.set_visible(False)
        self.map_fig_ax.set(xlabel = "x [km]", ylabel = "y [km]")
        # initialize artists
        self.track_ln, = self.map_fig_ax.plot([], [], "k.", ms=.1, picker=True)
        self.track_start_ln, = self.map_fig_ax.plot([], [], "go", ms=3, label="start")
        self.track_end_ln, = self.map_fig_ax.plot([], [], "ro", ms=3, label="end")
        # pack mpl figure in canvas window
        self.map_dataCanvas = FigureCanvasTkAgg(self.map_fig, self.basemap_window)
        self.map_dataCanvas.get_tk_widget().pack(in_=self.map_display, side="bottom", fill="both", expand=1)
        self.map_toolbar = NavigationToolbar2Tk(self.map_dataCanvas, self.basemap_window)
        self.map_dataCanvas._tkcanvas.pack()
        self.basemap_state = 1
        self.draw_cid = self.map_fig.canvas.mpl_connect("draw_event", self.update_bg)
        self.pick_cid = self.map_fig.canvas.mpl_connect("pick_event", self.on_pick)


    def set_vars(self):
        # initialize arrays to hold track nav info
        self.x = np.array(())
        self.y = np.array(())
        self.track_name = np.array(()).astype(dtype=np.str)
        self.loaded_tracks = np.array(()).astype(dtype=np.str)
        self.start_x = np.array(())
        self.start_y = np.array(())
        self.end_x = np.array(())
        self.end_y = np.array(())
        self.legend = None
        self.pick_loc = None
        self.profile_track = None


    # map is a method to plot the basemap in the basemap window
    def map(self, map_path):
        # pull track up on dem basemap
        if map_path:
            print("Loading Basemap: ", map_path.split("/")[-1])
            try:
                # read in basemap
                with rio.open(map_path, mode="r") as dataset:
                    # downsample if raster is too large
                    fac = 1
                    if dataset.height >= 3e3 or dataset.width >= 3e3:
                        fac = 4
                    elif dataset.height >= 2e3 or dataset.width >= 2e3:
                        fac = 3
                    elif dataset.height >= 1e3 or dataset.width >= 1e3:
                        fac = 2
                    data = dataset.read(
                        out_shape=(dataset.count, int(dataset.height // fac), int(dataset.width // fac)),
                        resampling=rio.enums.Resampling.nearest
                    )
                    self.bmcrs = dataset.crs
                # stack bands into numpy array
                im = np.dstack((data))
                if im.shape[-1] == 1:
                    im = im.reshape(im.shape[0], -1)
                cmin = np.nanmin(im)
                cmax = np.nanmax(im)
                self.bm_im.set_clim([cmin, cmax])
                self.bm_im.set_data(im)
                # set bm image extent based on raster bounds - convert from m to km
                self.bm_im.set_extent([_i*1e-3 for _i in[dataset.bounds.left, dataset.bounds.right,
                dataset.bounds.bottom, dataset.bounds.top]])
                # save un-zoomed view to toolbar
                self.map_toolbar.push_current()
                self.map_fig_ax.set_visible(True)
                self.map_dataCanvas.draw()

            except Exception as err:
                print("basemap load error: " + str(err))
                pass


    # set_track is a method to pass the track name loaded in profile view to the basemap class
    def set_track(self, fn):
        self.profile_track = fn


    # set_nav is a method to update the navigation data plotted on the basemap
    def set_nav(self, fn, navdf):
        # skip if track already loaded to basemap
        if fn in self.track_name:
            return

        # transform navcrs to basemap crs
        x, y = pyproj.transform(
            self.navcrs,
            self.bmcrs,
            navdf["lon"].to_numpy(),
            navdf["lat"].to_numpy(),
        )
        # convert from m to km
        x = x*1e-3
        y = y*1e-3
        # add x and y coords to x and y coord arrays
        self.x = np.append(self.x, x)
        self.y = np.append(self.y, y)
        # add name to array to match with x,y
        self.track_name = np.append(self.track_name, np.repeat(fn, len(x)))
        self.start_x = np.append(self.start_x, x[0])
        self.start_y = np.append(self.start_y, y[0])
        self.end_x = np.append(self.end_x, x[-1])
        self.end_y = np.append(self.end_y, y[-1])
        # add name to list to match with endpoints
        self.loaded_tracks = np.append(self.loaded_tracks, fn)


    # plot_tracks is a method to plot track geom
    def plot_tracks(self):
        # if track_viz variable is true, add all track points to appropriate lines
        if self.track_viz.get():
            # set track line data
            self.track_ln.set_data(self.x, self.y)
            # set track ending line data
            self.track_start_ln.set_data(self.start_x, self.start_y)
            self.track_end_ln.set_data(self.end_x, self.end_y)

            self.map_fig_ax.axis([(np.amin(self.x)- 15),(np.amax(self.x)+ 15),(np.amin(self.y)- 15),(np.amax(self.y)+ 15)])
        # otherwise just set track points from last line to appropriate lines
        else:
            # set track ending line data
            idx = np.where(self.loaded_tracks == self.profile_track)[0]
            self.track_start_ln.set_data(self.start_x[idx], self.start_y[idx])
            self.track_end_ln.set_data(self.end_x[idx], self.end_y[idx])
            # set track line data
            idx = np.where(self.track_name == self.profile_track)[0]
            self.track_ln.set_data(self.x[idx], self.y[idx])
            self.map_fig_ax.axis([(np.amin(self.x[idx])- 15),(np.amax(self.x[idx])+ 15),(np.amin(self.y[idx])- 15),(np.amax(self.y[idx])+ 15)])

        if not self.legend:
            self.legend = self.map_fig_ax.legend()
        self.map_dataCanvas.draw() 
        self.blit()


    # plot_idx is a method to plot the location of a click event on the datacanvas to the basemap
    def plot_idx(self, fn, idx):
        # basemap open, plot picked location regardless of picking state
        if self.basemap_state == 1 and len(self.x) > 0:
            # plot pick location on basemap
            if self.pick_loc:
                self.pick_loc.remove()
            self.pick_loc = self.map_fig_ax.scatter(self.x[self.track_name == fn][idx], 
                                                    self.y[self.track_name == fn][idx], 
                                                    c="b", marker="X", zorder=3)
            self.blit()

        
    # basemap_close is a method to close the basemap window
    def basemap_close(self, event=None):
        self.basemap_window.destroy()
        self.basemap_state = 0


    # get_state is a mathod to get the basemap state
    def get_state(self):
        return self.basemap_state

    
    # clear_basemap is a method to clear the basemap 
    def clear_nav(self):
        # clear arrays
        self.track_name = np.array(()).astype(dtype=np.str)
        self.loaded_tracks = np.array(()).astype(dtype=np.str)
        self.x = np.array(())
        self.y = np.array(())
        self.start_x = np.array(())
        self.start_y = np.array(())
        self.end_x = np.array(())
        self.end_y = np.array(())
        # set lines
        self.track_ln.set_data(self.x, self.y)
        self.track_start_ln.set_data(self.start_x, self.start_y)
        self.track_end_ln.set_data(self.end_x, self.end_y)

        if self.legend:
            self.legend.remove()
            self.legend = None

        if self.pick_loc:
            self.pick_loc.remove()
            self.pick_loc = None

        self.map_fig.canvas.draw()


    def safe_draw(self):
        """temporarily disconnect the draw_event callback to avoid recursion"""
        canvas = self.map_fig.canvas
        canvas.mpl_disconnect(self.draw_cid)
        canvas.draw()
        self.draw_cid = canvas.mpl_connect("draw_event", self.update_bg)


    def update_bg(self, event=None):
        """
        when the figure is resized, hide picks, draw everything,
        and update the background.
        """
        if self.pick_loc:
            self.pick_loc.set_visible(False)
            self.safe_draw()
            self.axbg = self.map_dataCanvas.copy_from_bbox(self.map_fig_ax.bbox)
            self.pick_loc.set_visible(True)
            self.blit()
        else:
            self.safe_draw()
            self.axbg = self.map_dataCanvas.copy_from_bbox(self.map_fig_ax.bbox)
            self.blit()


    def blit(self):
        """
        update the figure, without needing to redraw the
        "axbg" artists.
        """
        self.map_fig.canvas.restore_region(self.axbg)
        if self.pick_loc:
            self.map_fig_ax.draw_artist(self.pick_loc)
        self.map_fig.canvas.blit(self.map_fig_ax.bbox)


    # load all tracks within a directory to basemap
    def load_tracks(self, dir = False):
        if dir:
            tmp_datPath = ""
            # select input file
            tmp_datPath = tk.filedialog.askdirectory(title="select folder",
                                        initialdir=self.datPath,
                                        mustexist=True) 
            # if input selected, clear impick canvas, ingest data and pass to impick
            if tmp_datPath:
                # get list of data files in dir
                flist = glob.glob(tmp_datPath + "/*")
                print(tmp_datPath)

        else: 
            flist = ""
            # select input files
            flist = tk.filedialog.askopenfilenames(title="select files",
                                        initialdir=self.datPath, 
                                        multiple=True) 
            if flist:
                flist = list(flist)

            # iterate through file list and retrieve navdat from proper getnav function
        for f in flist:

            if f.endswith("h5"):
                navdf = navparse.getnav_oibAK_h5(f, self.navcrs, self.body)
                fn = f.split("/")[-1].rstrip(".h5")
            elif f.endswith("mat"):
                try:
                    navdf = navparse.getnav_cresis_mat(f, self.navcrs, self.body)
                    fn = f.split("/")[-1].rstrip(".mat")
                except:
                    navdf = navparse.getnav_oibAK_h5(f, self.navcrs, self.body)
                    fn = f.split("/")[-1].rstrip(".mat")
            elif f.lower().endswith("dzg"):
                navdf = navparse.getnav_gssi(f, self.navcrs, self.body)
                fn = f.split("/")[-1].rstrip(".DZG")
            elif f.endswith("tab"):
                navdf = navparse.getnav_sharad(f, self.navcrs, self.body)
                fn = f.split("/")[-1].rstrip("_geom.tab")
            else:
                continue
            self.set_nav(fn, navdf)

        # update datPath
        self.datPath = os.path.dirname(os.path.abspath(f)) + "/"
        # update extent
        self.plot_tracks()


    # settings menu
    def settings(self):
        settingsWindow = tk.Toplevel(self.basemap_window)

        row = tk.Frame(settingsWindow)
        row.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        lab = tk.Label(row, width=10, text="cmap", anchor="w")
        lab.pack(side=tk.LEFT)
        tk.Radiobutton(row,text="greys_r", variable=self.cmap, value="Greys_r").pack(side="top",anchor="w")
        tk.Radiobutton(row,text="gray", variable=self.cmap, value="gray").pack(side="top",anchor="w")
        tk.Radiobutton(row,text="terrain", variable=self.cmap, value="terrain").pack(side="top",anchor="w")

        row = tk.Frame(settingsWindow)
        row.pack(side=tk.TOP, anchor="c")
        b1 = tk.Button(row, text="save",
                    command=self.updateSettings)
        b1.pack(side="left")
        b2 = tk.Button(row, text="close", command=settingsWindow.destroy)
        b2.pack(side="left")


    # update settings
    def updateSettings(self):
        # pass cmap
        self.bm_im.set_cmap(self.cmap.get())
        # redraw
        self.map_dataCanvas.draw() 


    # on_pick gets the picked track from user click
    def on_pick(self, event):
        # determine which track was selected
        xdata = event.mouseevent.xdata
        idx = utils.find_nearest(self.x, xdata)
        track = self.track_name[idx]
        # pass track to impick
        if (track != self.profile_track) and (tk.messagebox.askyesno("Load","Load track: " + str(track) + "?") == True):
            self.to_gui(self.datPath, track)