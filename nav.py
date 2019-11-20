import numpy as np
import gdal, osr
import sys


class Dem:
  # Holds an array of DEM data and relevant metadata
  def __init__(self,dem_path):
    src_dem = gdal.Open(dem_path,GA_ReadOnly)
    self.csys = src_dem.GetProjection()
    self.gt = src_dem.GetGeoTransform()
    self.nd = src_dem.GetRasterBand(1).GetNoDataValue()
    if(self.nd == None):
      self.nd = -np.finfo('d').max
    self.data = np.array(src_dem.GetRasterBand(1).ReadAsArray())
    src_dem = None
    
class nav:
  # A list of loc objects, representing a path. Along with some useful
  # metadata
  def __init__(self, csys = None, navdat = None):
    self.navdat = navdat
    self.csys = csys


  def copy(self):
    # Returns a copy of the Pointlist
    return nav(self.csys,self.navdat)


  def transform(self,targ):
    #print(self)
    # Transforms a Pointlist to another coordinate system, can read Proj4 format
    # and WKT

    navdat = self.copy()

    source = osr.SpatialReference()  
    target = osr.SpatialReference()  

    # Deciding whether the coordinate systems are Proj4 or WKT
    sc0 = self.csys[0]
    if(sc0 == 'G' or sc0 == 'P'):
      source.ImportFromWkt(navdat.csys)
    else:
      source.ImportFromProj4(navdat.csys)

    tc0 = targ[0]
    if(tc0 == 'G' or tc0 == 'P'):
      target.ImportFromWkt(targ)
    elif(tc0 == '+'):
      target.ImportFromProj4(targ)
    else:
      print("Unrecognized target coordinate system:")
      print(targ)
      sys.exit()

    navdat_xform = np.zeros(navdat.navdat.shape)

    # The actual transformation
    transform = osr.CoordinateTransformation(source, target)
    xform = transform.TransformPoint

    for _i in range(navdat.navdat.shape[0]):      
      navdat_xform[_i,:] = np.asarray(xform(navdat.navdat[_i,0],navdat.navdat[_i,1],navdat.navdat[_i,2]))
    navdat.navdat = navdat_xform
    navdat.csys = targ
    return navdat

def transformPt(nav, in_csys, out_csys):
  # Transforms a point to another coordinate system, can read Proj4 format
  # and WKT

  # The actual transformation
  transform = osr.CoordinateTransformation(in_csys, out_csys)
  npt = transform.TransformPoint(nav[:,0],nav[:,1]) # x, y, z data list

  return npt