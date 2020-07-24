### imports ###
import numpy as np
import pandas as pd
import gdal, osr
import sys
import pyproj
    
class navdat:
  # list of loc objects, representing a path. Along with some useful methods
  def __init__(self, crs = None, df = None):
    #: str: coordinate system, Proj4 or WKT 
    self.crs = crs
    #: pandas dataframe (tnum x 3) df object [lon, lat, elev]
    self.df = pd.DataFrame(columns=["lon","lat","elev"])

    self.xyz = {
    "mars": "+proj=geocent +a=3396190 +b=3376200 +no_defs",
    "moon": "+proj=geocent +a=1737400 +b=1737400 +no_defs",
    "earth": "+proj=geocent +a=6378140 +b=6356750 +no_defs",
    }

  def transform(self,body):
    xform = pyproj.transformer.Transformer.from_crs(self.crs, self.xyz[body])
    x, y = xform.transform(self.df["lon"].tolist(), self.df["lat"].tolist(), direction="FORWARD")
    return np.asarray(x), np.asarray(y)

def euclid_dist(xarray, yarray):
  dist = np.zeros_like(xarray)
  dist[1:] = np.cumsum(np.sqrt(np.diff(xarray) ** 2.0 + np.diff(yarray) ** 2.0))
  return dist