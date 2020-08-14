"""
basemap class is a tkinter frame which handles the NOSEpick basemap
"""
### imports ###
from nav import navparse
import numpy as np
import tkinter as tk
import rasterio as rio
import os, pyproj
import matplotlib as mpl
mpl.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

class basemap(tk.Frame):
    def __init__(self, parent, datPath, navcrs, body):
        self.parent = parent
        self.datPath = datPath
        self.navcrs = navcrs
        self.body = body
        # create tkinter toplevel window to display basemap
        self.basemap_window = tk.Toplevel(self.parent)
        img = tk.PhotoImage(file="../recs/basemap_icon.png")
        self.basemap_window.tk.call("wm", "iconphoto", self.basemap_window._w, img)
        self.basemap_window.config(bg="#d9d9d9")
        self.basemap_window.title("NOSEpick - Map Window")
        self.map_display = tk.Frame(self.basemap_window)
        self.map_display.pack(side="bottom", fill="both", expand=1)
        # bind ctrl-q key to basemap_close()
        self.basemap_window.bind("<Control-q>", self.basemap_close)
        # bind x-out to basemap_close()
        self.basemap_window.protocol("WM_DELETE_WINDOW", self.basemap_close)
        # initialize arrays to hold track nav info
        self.x = np.array(())
        self.y = np.array(())
        self.trackName = np.array(()).astype(dtype=np.str)
        self.start_x = np.array(())
        self.start_y = np.array(())
        self.end_x = np.array(())
        self.end_y = np.array(())
        self.legend = None
        self.pick_loc = None
        self.track = None
        self.basemap_state = 0
        self.cmap = tk.StringVar(value="Greys_r")
        self.setup()


    # setup the wkinter frame
    def setup(self):
        # show basemap figure in basemap window
        # generate menubar
        menubar = tk.Menu(self.basemap_window)
        fileMenu = tk.Menu(menubar, tearoff=0)
        fileMenu.add_command(label="load tracks", command=self.load_tracks)
        fileMenu.add_command(label="clear nav", command=self.clear_nav)
        fileMenu.add_command(label="preferences", command=self.settings)
        fileMenu.add_command(label="exit       [ctrl+q]", command=self.basemap_close)
        # add items to menubar
        menubar.add_cascade(label="file", menu=fileMenu)
        # add the menubar to the window
        self.basemap_window.config(menu=menubar)
        # initialize the basemap figure
        self.map_fig = mpl.figure.Figure()
        self.map_fig.patch.set_facecolor(self.parent.cget("bg"))
        self.map_fig_ax = self.map_fig.add_subplot(111)
        self.bm_im = self.map_fig_ax.imshow(np.ones((100,100)), cmap=self.cmap.get(), aspect="auto")
        self.map_fig_ax.set_visible(False)
        self.map_fig_ax.set(xlabel = "x [m]", ylabel = "y [m]")
        # initialize artists
        self.track, = self.map_fig_ax.plot(self.x, self.y, "k.", ms=.1)    # empty line for track nav
        self.track_start, = self.map_fig_ax.plot(self.start_x, self.start_y, "go", ms=3, label="start")
        self.track_end, = self.map_fig_ax.plot(self.end_x, self.end_y, "ro", ms=3, label="end")
        # pack mpl figure in canvas window
        self.map_dataCanvas = FigureCanvasTkAgg(self.map_fig, self.basemap_window)
        self.map_dataCanvas.get_tk_widget().pack(in_=self.map_display, side="bottom", fill="both", expand=1)
        self.map_toolbar = NavigationToolbar2Tk(self.map_dataCanvas, self.basemap_window)
        self.map_dataCanvas._tkcanvas.pack()
        self.basemap_state = 1
        self.draw_cid = self.map_fig.canvas.mpl_connect("draw_event", self.update_bg)
        self.pick_cid = self.map_fig.canvas.mpl_connect("pick_event", self.on_pick)


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
                self.bm_im.set_extent([dataset.bounds.left, dataset.bounds.right,
                dataset.bounds.bottom, dataset.bounds.top])
                # save un-zoomed view to toolbar
                self.map_toolbar.push_current()
                self.map_fig_ax.set_visible(True)
                self.map_dataCanvas.draw()

            except Exception as err:
                print("basemap load error: " + str(err))
                pass


    # set_nav is a method to update the navigation data plotted on the basemap
    def set_nav(self, fn, navdf, dirFlag = False):
        # transform navcrs to basemap crs
        x, y = pyproj.transform(
            self.navcrs,
            self.bmcrs,
            navdf["lon"].to_numpy(),
            navdf["lat"].to_numpy(),
        )
        self.x = np.append(self.x, x)
        self.y = np.append(self.y, y)
        self.trackName = np.append(self.trackName, np.repeat(fn, len(x)))
        self.start_x = np.append(self.start_x, x[0])
        self.start_y = np.append(self.start_y, y[0])
        self.end_x = np.append(self.end_x, x[-1])
        self.end_y = np.append(self.end_y, y[-1])
        # plot lat, lon atop basemap im
        self.track.set_data(self.x, self.y)
        # zoom in to track
        # annotate each end of the track
        self.track_start.set_data(self.start_x, self.start_y)
        self.track_end.set_data(self.end_x, self.end_y)
        if not self.legend:
            self.legend = self.map_fig_ax.legend()
        if not dirFlag:
                self.map_fig_ax.axis([(np.amin(x)- 15000),(np.amax(x)+ 15000),(np.amin(y)- 15000),(np.amax(y)+ 15000)])
                self.map_dataCanvas.draw() 
        # self.basemap_window.title("NOSEpick - Map Window: " + os.path.splitext(floadName.split("/")[-1])[0])



    # plot_idx is a method to plot the location of a click event on the datacanvas to the basemap
    def plot_idx(self, fn, idx):
        # basemap open, plot picked location regardless of picking state
        if self.basemap_state == 1:
            # plot pick location on basemap
            if self.pick_loc:
                self.pick_loc.remove()
            self.pick_loc = self.map_fig_ax.scatter(self.x[self.trackName == fn][idx], 
                                                    self.y[self.trackName == fn][idx], 
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
        self.x = np.array(())
        self.y = np.array(())
        self.start_x = np.array(())
        self.start_y = np.array(())
        self.end_x = np.array(())
        self.end_y = np.array(())
        self.track.set_data(self.x, self.y)
        self.track_start.set_data(self.start_x, self.start_y)
        self.track_end.set_data(self.end_x, self.end_y)

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
    def load_tracks(self):
        tmp_datPath = ""
        # select input file
        tmp_datPath = tk.filedialog.askdirectory(title="load tracks",
                                       initialdir=self.datPath,
                                       mustexist=True) 
        # if input selected, clear impick canvas, ingest data and pass to impick
        if tmp_datPath:
            self.datPath = tmp_datPath
            # get list of data files in dir
            flist = os.listdir(tmp_datPath)
            # iterate through file list and retrieve navdat from proper getnav function
            for f in flist:
                if f.endswith("h5"):
                    navdf = navparse.getnav_oibAK_h5(self.datPath + "/" + f, self.navcrs, self.body)
                    fn = f.rstrip(f.split(".")[-1])
                elif f.lower().endswith("dzg"):
                    navdf = navparse.getnav_gssi(self.datPath + "/" + f, self.navcrs, self.body)
                    fn = f.rstrip(f.split(".")[-1])
                elif f.endswith("tab"):
                    navdf = navparse.getnav_sharad(self.datPath + "/" + f, self.navcrs, self.body)
                    fn = f.rstrip(f.split("_")[-2])
                else:
                    continue
                self.set_nav(fn, navdf, dirFlag = True)
            # update extent
            self.map_fig_ax.axis([(np.amin(self.x)- 15000),(np.amax(self.x)+ 15000),(np.amin(self.y)- 15000),(np.amax(self.y)+ 15000)])
            self.map_dataCanvas.draw() 



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
        return