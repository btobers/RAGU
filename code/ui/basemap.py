"""
basemap class is a tkinter frame which handles the NOSEpick basemap
"""
### imports ###
import numpy as np
import tkinter as tk
import rasterio as rio
import os, pyproj
import matplotlib as mpl
mpl.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

class basemap(tk.Frame):
    def __init__(self, parent, map_path):
        self.parent = parent
        self.map_loadName = map_path
        # create tkinter toplevel window to display basemap
        self.basemap_window = tk.Toplevel(self.parent)
        img = tk.PhotoImage(file='../recs/basemap_icon.png')
        self.basemap_window.tk.call('wm', 'iconphoto', self.basemap_window._w, img)
        self.basemap_window.config(bg="#d9d9d9")
        self.basemap_window.title("NOSEpick - Map Window")
        self.map_display = tk.Frame(self.basemap_window)
        self.map_display.pack(side="bottom", fill="both", expand=1)
        # bind ctrl-q key to basemap_close()
        self.basemap_window.bind("<Control-q>", self.basemap_close)
        # bind x-out to basemap_close()
        self.basemap_window.protocol("WM_DELETE_WINDOW", self.basemap_close)
        self.pick_loc = None
        self.track = None
        self.basemap_state = 0


    # map is a method to plot the basemap in the basemap window
    def map(self):
        # pull track up on dem basemap
        if self.map_loadName:
            print("Loading Basemap: ", self.map_loadName.split("/")[-1])
            try:
                # open geotiff with rasterio
                dataset = rio.open(self.map_loadName, mode="r")
                self.bmcrs = dataset.crs
                im = np.dstack((dataset.read())) # np.dstack((dataset.read(1), dataset.read(2), dataset.read(3), dataset.read(4)))
                # # show basemap figure in basemap window
                self.map_fig = mpl.figure.Figure()
                self.map_fig.patch.set_facecolor(self.parent.cget('bg'))
                self.map_fig_ax = self.map_fig.add_subplot(111)
                self.map_fig_ax.imshow(im, cmap="Greys_r", aspect="auto",
                        extent=[dataset.bounds.left, dataset.bounds.right,
                        dataset.bounds.bottom, dataset.bounds.top])
                self.map_fig_ax.set(xlabel = "x [m]", ylabel = "y [m]")
                self.map_dataCanvas = FigureCanvasTkAgg(self.map_fig, self.basemap_window)
                self.map_dataCanvas.get_tk_widget().pack(in_=self.map_display, side="bottom", fill="both", expand=1)
                self.map_toolbar = NavigationToolbar2Tk(self.map_dataCanvas, self.basemap_window)
                # save un-zoomed view to toolbar
                self.map_toolbar.push_current()
                self.map_dataCanvas._tkcanvas.pack()
                self.map_dataCanvas.draw()
                self.basemap_state = 1
                self.draw_cid = self.map_fig.canvas.mpl_connect('draw_event', self.update_bg)
                
            except Exception as err:
                print("basemap load error: " + str(err))
                pass


    # set_nav is a method to update the navigation data plotted on the basemap
    def set_nav(self, floadName, navdf, navcrs):
        # transform navcrs to basemap crs
        self.x, self.y = pyproj.transform(
            navcrs,
            self.bmcrs,
            navdf["lon"].to_numpy(),
            navdf["lat"].to_numpy(),
        )
        # plot lat, lon atop basemap im
        self.track, = self.map_fig_ax.plot(self.x, self.y, "k")
        # zoom in to 10 km from track on all sides
        self.map_fig_ax.axis([(np.amin(self.x)- 15000),(np.amax(self.x)+ 15000),(np.amin(self.y)- 15000),(np.amax(self.y)+ 15000)])
        # annotate each end of the track
        self.track_start, = self.map_fig_ax.plot(self.x[0], self.y[0],'go',label='start')
        self.track_end, = self.map_fig_ax.plot(self.x[-1] , self.y[-1],'ro',label='end')
        self.legend = self.map_fig_ax.legend()  
        self.basemap_window.title("NOSEpick - Map Window: " + os.path.splitext(floadName.split("/")[-1])[0])
        self.map_dataCanvas.draw() 


    # plot_idx is a method to plot the location of a click event on the datacanvas to the basemap
    def plot_idx(self, idx):
        idx = idx
        # basemap open, plot picked location regardless of picking state
        if self.basemap_state == 1:
            # plot pick location on basemap
            if self.pick_loc:
                self.pick_loc.remove()
            self.pick_loc = self.map_fig_ax.scatter(self.x[idx],self.y[idx],c="b",marker="X",zorder=3)
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
        if self.track:
            self.track.remove()
            self.legend.remove()
            self.track_start.remove()
            self.track_end.remove()
        if self.pick_loc:
            self.pick_loc.remove()
            self.pick_loc = None
        self.map_fig.canvas.draw()

    def safe_draw(self):
        """temporarily disconnect the draw_event callback to avoid recursion"""
        canvas = self.map_fig.canvas
        canvas.mpl_disconnect(self.draw_cid)
        canvas.draw()
        self.draw_cid = canvas.mpl_connect('draw_event', self.update_bg)


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