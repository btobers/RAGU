import h5py
import numpy as np
from tools import *
import matplotlib.pyplot as plt

def savePick(self):
    # save picks
    if len(self.xln_old) > 0 and self.save_warning() is True:
        self.f_saveName = filedialog.asksaveasfilename(initialdir = "./",title = "Save As",filetypes = (("comma-separated values","*.csv"),))
        if self.f_saveName:
            v_ice = 3e8/np.sqrt(3.15)
            lon = []
            lat = []
            elev_air = []
            twtt_surf = []
            twtt_bed = []
            thick = []
            # get necessary data from radargram for pick locations
            # iterate through pick_dict layers
            num_pic_lyr = self.pick_layer
            for _i in range(num_pic_lyr):
                num_pt = len(np.where(self.pick_dict["layer_" + str(_i)] != -1)[0])
                pick_idx = np.where(self.pick_dict["layer_" + str(_i)] != -1)[0]
                for _j in range(num_pt):
                    lon.append(self.data["navdat"][pick_idx[_j]].x)
                    lat.append(self.data["navdat"][pick_idx[_j]].y)
                    elev_air.append(self.data["navdat"][pick_idx[_j]].z)
                    twtt_surf.append(self.data["twtt_surf"][pick_idx[_j]])
                    twtt_bed.append(self.pick_dict["layer_" + str(_i)][pick_idx[_j]])
                    thick.append(((twtt_bed[_j]-twtt_surf[_j])*v_ice)/2)
            header = "lon,lat,elev_air,twtt_surf,twtt_bed,thick"
            np.savetxt(self.f_saveName, np.column_stack((np.asarray(lon),np.asarray(lat),np.asarray(elev_air),np.asarray(twtt_surf),np.asarray(twtt_bed),np.asarray(thick))), delimiter=",", newline="\n", fmt="%.8f", header=header, comments="")
            print("Picks exported: ", self.f_saveName)




