import numpy as np
import gdal, osr

class tools:
  # NOSEpick tools class
  #  - pick optimization based on windowed amplitude
  #  - trace viewing
  def __init__(self, master, pickData):
    self.lat = lat
    self.lon = lon
    self.pickData = pickData

  # def trace_view(self):
  #     # show individual trace view along with initial pick location

  # def amp_window(self):
  #     # wubdiw initial pick sample to find max amplitude

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

class Loc:
  # A location in 3D space, either in cartesian or geodetic coordinates
  # The two are switched between often in this program so they are just
  # combined. X is the same field as longitude, Y is the same field as
  # latitude, Z is the same field as the radius.
  def __init__(self,x,y,z):
    self.x = x
    self.y = y
    self.z = z
    self.ol = False
    self.nd = False
    
  def __eq__(self, other):
    if(other is None):
      return False
    else:
      return(self.x == other.x and self.y == other.y and self.z == other.z)
    
  def __ne__(self, other):
    return(not self.__eq__(other))
   
  def __str__(self):
    return('(' + str(self.x) + ',' + str(self.y) + ',' + str(self.z) + ')')
    
  def __add__(self,vec):
    # Only allowed to add vectors to points
    return Loc(self.x + vec.i, self.y + vec.j, self.z + vec.k)
    
  def __radd__(self,vec):
    return self.__add__(vec)
    
  def __sub__(self,vec):
    # Only allowed to subtract vectors from points
    return Loc(self.x - vec.i, self.y - vec.j, self.z - vec.k)
    
  def __rsub__(self,vec):
    return self.__add__(vec)
    
  def copy(self):
    return Loc(self.x, self.y, self.z)
    
  def topix(self,dem):
    # This transforms a point to an (x,y) pixel location on a DEM using the input geotransform
    # IF YOU USE THIS ON ITS OWN WITHOUT THE toground() FUNCTION
    # FOR A Path MAKE SURE THAT THE POINT COORDINATES ARE IN THE
    # SAME COORDINATE SYSTEM AS THE GEOTRANSFORM
      
    gt = dem.gt
      
    x = int((gt[0] - self.x)/-gt[1])
    y = int((gt[3] - self.y)/-gt[5])
    
    ## Out of bounds stuff
    #if(x >= dem.data.shape[1]):
    #  x = dem.data.shape[1] - 1
      
    #if(y >= dem.data.shape[0]):
    #  y = dem.data.shape[0] - 1
    
    #if(x < 0):
    #  x = 0
    
    #if(y < 0):
    #  y = 0
    
    ## Other option for out of bounds stuff  
    if(x<0 or y <0 or x >= dem.data.shape[1] or y >= dem.data.shape[0]):
      #print('Requested data off DEM warning',[x,y],[self.x,self.y,self.z])
      #print(x,dem.data.shape[1],y,dem.data.shape[0])
      return Loc(-1,-1,0)
  
    out = Loc(x,y,0)
    
    # SPECIFIC FOR MOLA  
    #if(y < 116 or y > 22412):
    #  out.ol = True

    return out
 
  def equals(self, other):
    # Checks equality of two points
    if(self.x == other.x and self.y == other.y and self.z == other.z):
      return True
      
    return False
     
class Path:
  # A list of loc objects, representing a path. Along with some useful
  # metadata
  def __init__(self, csys = None, pts = []):
    self.pts = pts
    self.csys = csys
        
  def __setitem__(self,i,item):
    self.pts[i] = item
    
  def __getitem__(self,i):
    return self.pts[i]

  def __len__(self):
    return len(self.pts)
  
  def append(self,Loc):
    self.pts.append(Loc)
  
  def copy(self):
    # Returns a copy of the Pointlist
    return Path(self.csys,self.pts[:])
    
  def transform(self,targ):
    #print(self)
    # Transforms a Pointlist to another coordinate system, can read Proj4 format
    # and WKT
    
    pts = self.copy()
    
    source = osr.SpatialReference()  
    target = osr.SpatialReference()  

    # Deciding whether the coordinate systems are Proj4 or WKT
    sc0 = pts.csys[0]
    if(sc0 == 'G' or sc0 == 'P'):
      source.ImportFromWkt(pts.csys)
    else:
      source.ImportFromProj4(pts.csys)

    tc0 = targ[0]
    if(tc0 == 'G' or tc0 == 'P'):
      target.ImportFromWkt(targ)
    elif(tc0 == '+'):
      target.ImportFromProj4(targ)
    else:
      print("Unrecognized target coordinate system:")
      print(targ)
      sys.exit()

    # The actual transformation
    transform = osr.CoordinateTransformation(source, target)
    xform = transform.TransformPoint
    #print(pts[1].z)
    for i in range(len(pts)):
      #print(pts[1].z)
      #print(type(pts[i].x),type(pts[i].y),type(pts[i].z))
      #print('orig',str(pts[i]))
      npt = list(xform(pts[i].x,pts[i].y,pts[i].z))
      pts[i] = Loc(npt[0],npt[1],npt[2])
      #print('xform',str(pts[i]))

    pts.csys = targ
    return pts
  
  def toground(self, dem, outsys = None):
    # Function will get the points on the ground directly below a list of points,
    # this is not destructive and returns a new list 
    grd = self.copy() # copy to store on-ground points
    origsys = grd.csys

    # Transforming to the DEM coordinate system so the geotransform math works
    grd = grd.transform(dem.csys)

    # Iterate through the points and get the points below them
    for i in range(len(grd)):
      zpix = grd[i].topix(dem)
      if(zpix.x == -1 and zpix.y == -1):
        grd[i].z = dem.nd
      else:
        grd[i].z = float(dem.data[zpix.y][zpix.x])

    # Set coordinate systems for the new lists
    if(not(outsys is None)):
      grd = grd.transform(outsys)
    else:
      grd = grd.transform(origsys)

    return grd




def transformPt(pt, in_csys, out_csys):
  # Transforms a point to another coordinate system, can read Proj4 format
  # and WKT
    
  # source = osr.SpatialReference()  
  # target = osr.SpatialReference()  

  # Deciding whether the coordinate systems are Proj4 or WKT
  # sc0 = pt.csys[0]
  # if(sc0 == 'G' or sc0 == 'P'):
  #   source.ImportFromWkt(pt.csys)
  # else:
  #   source.ImportFromProj4(pt.csys)

  # tc0 = targ[0]
  # if(tc0 == 'G' or tc0 == 'P'):
  #   target.ImportFromWkt(targ)
  # elif(tc0 == '+'):
  #   target.ImportFromProj4(targ)
  # else:
  #   print("Unrecognized target coordinate system:")
  #   print(targ)
  #   sys.exit()

  # The actual transformation
  transform = osr.CoordinateTransformation(in_csys, out_csys)
  npt = transform.TransformPoint(pt[0],pt[1]) # x, y, z data list

  return npt

