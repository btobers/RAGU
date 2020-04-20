import numpy as np
import tkinter as tk
import gdal, osr
import matplotlib as mpl
mpl.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import os
# from PIL import Image

class basemap(tk.Tk):
    def __init__(self, parent, map_path):
        self.parent = parent
        self.map_loadName = map_path
        # create tkinter toplevel window to display basemap
        self.basemap_window = tk.Toplevel(self.parent)
        img = tk.PhotoImage(file='lib/basemap.png')
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
                # open geotiff and convert coordinate systems to get lat long of image extent
                self.basemap_ds = gdal.Open(self.map_loadName)              # open raster
                self.basemap_im = self.basemap_ds.ReadAsArray()             # read input raster as array
                self.basemap_proj = self.basemap_ds.GetProjection()         # get coordinate system of input raster
                self.basemap_proj_xform = osr.SpatialReference()
                self.basemap_proj_xform.ImportFromWkt(self.basemap_proj)
                # Get raster georeference info 
                width = self.basemap_ds.RasterXSize
                height = self.basemap_ds.RasterYSize
                gt = self.basemap_ds.GetGeoTransform()
                if gt[2] != 0 or gt[4] != 0:
                    print('Geotransform rotation!')
                    print('gt[2]:ax '+ gt[2] + '\ngt[4]: ' + gt[4])
                    return
                # get image corner locations
                minx = gt[0]
                miny = gt[3]  + height*gt[5] 
                maxx = gt[0]  + width*gt[1]
                maxy = gt[3] 
                # show basemap figure in basemap window
                self.map_fig = mpl.figure.Figure()
                self.map_fig.patch.set_facecolor(self.parent.cget('bg'))
                self.map_fig_ax = self.map_fig.add_subplot(111)
                # if using rgb image, make sure the proper shape
                if self.basemap_im.shape[0] == 3 or self.basemap_im.shape[0] == 4:
                    self.basemap_im = np.dstack([self.basemap_im[0,:,:],self.basemap_im[1,:,:],self.basemap_im[2,:,:]])
                # display image in km
                self.map_fig_ax.imshow(self.basemap_im, cmap="Greys_r", aspect="auto", extent=[int(minx*1e-3), int(maxx*1e-3), int(miny*1e-3), int(maxy*1e-3)])
                self.map_fig_ax.set(xlabel = "x [km]", ylabel = "y [km]")
                self.map_dataCanvas = FigureCanvasTkAgg(self.map_fig, self.basemap_window)
                self.map_dataCanvas.get_tk_widget().pack(in_=self.map_display, side="bottom", fill="both", expand=1)
                self.map_toolbar = NavigationToolbar2Tk(self.map_dataCanvas, self.basemap_window)
                # self.map_toolbar.update()
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
    def set_nav(self, navdat, floadName):
        self.navdat = navdat
        if self.basemap_state == 1:
            # transform navdat to csys of geotiff   
            self.nav_transform = self.navdat.transform(self.basemap_proj)   
            # convert to km
            self.nav_transform.navdat = self.nav_transform.navdat * 1e-3
            # plot lat, lon atop basemap im
            self.track, = self.map_fig_ax.plot(self.nav_transform.navdat[:,0],self.nav_transform.navdat[:,1],"k")
            # zoom in to 10 km from track on all sides
            self.map_fig_ax.axis([(np.amin(self.nav_transform.navdat[:,0])- 15),(np.amax(self.nav_transform.navdat[:,0])+ 15),(np.amin(self.nav_transform.navdat[:,1])- 15),(np.amax(self.nav_transform.navdat[:,1])+ 15)])
            # annotate each end of the track
            self.track_start, = self.map_fig_ax.plot(self.nav_transform.navdat[0,0],self.nav_transform.navdat[0,1],'go',label='start')
            self.track_end, = self.map_fig_ax.plot(self.nav_transform.navdat[-1,0],self.nav_transform.navdat[-1,1],'ro',label='end')
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
            self.pick_loc = self.map_fig_ax.scatter(self.nav_transform.navdat[idx,0],self.nav_transform.navdat[idx,1],c="b",marker="D",zorder=3)
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