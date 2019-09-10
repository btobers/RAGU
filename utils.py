import ingester
import numpy as np
from tools import *
from tkinter import filedialog, messagebox


# a set of utility functions for NOSEpick GUI


def help():
    # help message box
    messagebox.showinfo("NOSEpick Instructions",
    """Nearly Optimal Subsurface Extractor:
    \n\n1. Load button to open radargram
    \n2. Click along reflector surface to pick
    \n\t\u2022<backspace> to remove the last
    \n\t\u2022<c> to remove all
    \n3. Radar and clutter buttons to toggle
    \n4. Next button to load next file
    \n5. Save button to export picks
    \n6. Map button to display basemap
    \n7. Exit button to close application""")


def open():
    # open radar data
    # bring up dialog box for user to load data file
    igst = ingester.ingester("h5py")
    f_loadName = filedialog.askopenfilename(initialdir = in_path,title = "Select file",filetypes = (("mat files","*.mat"),("all files","*.*")))
    return f_loadName


def savePick(data, pick_dict):
    # save picks
    if save_warning() is True:
        f_saveName = filedialog.asksaveasfilename(initialdir = "./",title = "Save As",filetypes = (("comma-separated values","*.csv"),))
        if f_saveName:
            v_ice = 3e8/np.sqrt(3.15)
            lon = []
            lat = []
            elev_air = []
            twtt_surf = []
            twtt_bed = []
            thick = []
            # get necessary data from radargram for pick locations
            # iterate through pick_dict layers
            num_pick_lyr = len(pick_dict)
            for _i in range(num_pick_lyr):
                num_pt = len(np.where(pick_dict["layer_" + str(_i)] != -1)[0])
                pick_idx = np.where(pick_dict["layer_" + str(_i)] != -1)[0]
                for _j in range(num_pt):
                    lon.append(data["navdat"][pick_idx[_j]].x)
                    lat.append(data["navdat"][pick_idx[_j]].y)
                    elev_air.append(data["navdat"][pick_idx[_j]].z)
                    twtt_surf.append(data["twtt_surf"][pick_idx[_j]])
                    twtt_bed.append(pick_dict["layer_" + str(_i)][pick_idx[_j]])
                    thick.append(((twtt_bed[_j]-twtt_surf[_j])*v_ice)/2)
            header = "lon,lat,elev_air,twtt_surf,twtt_bed,thick"
            np.savetxt(f_saveName, np.column_stack((np.asarray(lon),np.asarray(lat),np.asarray(elev_air),np.asarray(twtt_surf),np.asarray(twtt_bed),np.asarray(thick))), delimiter=",", newline="\n", fmt="%.8f", header=header, comments="")
            print("Picks exported: ", f_saveName)


def next_file(f_loadName):
    # load next data file in directory
    # get index of selected file in directory
    file_path = f_loadName.rstrip(f_loadName.split("/")[-1])
    file_list = os.listdir(file_path)
    file_list.sort()
    for _i in range(len(file_list)):
        if file_list[_i] == f_loadName.split("/")[-1]:
            file_index = _i
            
        # check if more files exist in directory following current file
        if file_index <= (len(file_list) - 1):
            f_loadName = (file_path + file_list[file_index])
            del xln[:]
            del yln[:]
            del xln_old[:]
            del yln_old[:]

            return f_loadName

        else:
            print("Note: " + f_loadName.split("/")[-1] + " is the last file in " + file_path)


def find_nearest(array,value):
    # return index in array with value closest to the passed value
    idx = (np.abs(array-value)).argmin()
    return idx