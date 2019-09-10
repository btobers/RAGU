import numpy as np
from tools import *
import matplotlib.pyplot as plt

class basmap:
    # basemap is a class which loads and handles the basemap
    def __init__(self):

    def basemap(self):
        # pull track up on dem basemap
        if self.f_loadName:
            self.map_loadName = filedialog.askopenfilename(initialdir = map_path, title = "Select file", filetypes = (("GeoTIFF files","*.tif"),("all files","*.*")))
        if self.map_loadName:
            print("Loading Basemap: ", self.map_loadName)
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
                    print('Geotraaxnsform rotation!')
                    print('gt[2]:ax '+ gt[2] + '\ngt[4]: ' + gt[4])
                    sys.exit()
                # get corner locations
                minx = gt[0]
                miny = gt[3]  + height*gt[5] 
                maxx = gt[0]  + width*gt[1]
                maxy = gt[3] 
                # transform navdat to csys of geotiff   
                self.nav_transform = self.data['navdat'].transform(self.basemap_proj)  
                # make list of navdat x and y data for plotting on basemap - convert to kilometers
                self.xdat = []
                self.ydat = []
                for _i in range(len(self.nav_transform)):
                    self.xdat.append(self.nav_transform[_i].x)
                    self.ydat.append(self.nav_transform[_i].y)
                # create new window and show basemap
                self.basemap_window = tk.Toplevel(self.master)
                self.basemap_window.protocol("WM_DELETE_WINDOW", self.basemap_close)
                self.basemap_window.title("NOSEpick - Map Window")
                self.map_display = Frame(self.basemap_window)
                self.map_display.pack(side="bottom", fill="both", expand=1)
                self.map_fig = mpl.figure.Figure()
                self.map_fig_ax = self.map_fig.add_subplot(111)
                self.map_fig_ax.imshow(self.basemap_im, cmap="gray", aspect="auto", extent=[minx, maxx, miny, maxy])
                self.map_fig_ax.set(xlabel = "x [km]", ylabel = "y [km]")
                self.map_dataCanvas = FigureCanvasTkAgg(self.map_fig, self.basemap_window)
                self.map_dataCanvas.get_tk_widget().pack(in_=self.map_display, side="bottom", fill="both", expand=1)
                self.map_toolbar = NavigationToolbar2Tk(self.map_dataCanvas, self.basemap_window)
                self.map_toolbar.update()
                self.map_dataCanvas._tkcanvas.pack()
                # plot lat, lon atop basemap im
                self.map_fig_ax.plot(self.xdat,self.ydat,"k")
                # convert axes to kilometers
                self.map_xticks = self.map_fig_ax.get_xticks()*1e-3
                self.map_yticks = self.map_fig_ax.get_yticks()*1e-3
                # shift xticks and yticks if zero is not at the lower left
                if minx != 0:
                    self.map_xticks = [x + abs(min(self.map_xticks)) for x in self.map_xticks] 
                if miny != 0:
                    self.map_yticks = [y + abs(min(self.map_yticks)) for y in self.map_yticks] 
                self.map_fig_ax.set_xticklabels(self.map_xticks)
                self.map_fig_ax.set_yticklabels(self.map_yticks)
                # zoom in to 100 km from track on all sides
                self.map_fig_ax.set(xlim = ((min(self.xdat)- 100000),(max(self.xdat)+ 100000)), ylim = ((min(self.ydat)- 100000),(max(self.ydat)+ 100000)))
                # annotate each end of the track
                self.map_fig_ax.plot(self.xdat[0],self.ydat[0],'go',label='start')
                self.map_fig_ax.plot(self.xdat[-1],self.ydat[-1],'ro',label='end')
                self.map_fig_ax.legend()                
                self.map_dataCanvas.draw()
                self.basemap_state = 1
                
            except Exception as err:
                print("basemap load error: " + str(err))
                pass






