"""
NOSEpick - currently in development stages
created by: Brandon S. Tober and Michael S. Christoffersen
date: 25JUN19
last updated: 14NOV19
environment requirements in nose_env.yml
"""

### IMPORTS ###
import gui
import tkinter as tk
from tkinter import font

### USER SPECIFIED VARS ###
in_path = "/zippy/MARS/targ/supl/UAF/2019/reproc/"
# in_path = "/zippy/MARS/orig/supl/WISE/blocks/"
# in_path = "/home/btober/Desktop/"
# in_path = "/mnt/Swaps/MARS/targ/supl/UAF/2019/hdf5/"
# out_path = "/home/anomalocaris/Desktop"
out_path = "/zippy/MARS/targ/supl/UAF/2010/picks/"
map_path = "/zippy/MARS/targ/supl/grid-AKDEM/"
# map_path = "/mnt/Swaps/MARS/orig/supl/gis/projects/qgis/OIB-AK_radar/"

### INITIALIZE ###
root = tk.Tk()

# get screen size - open root window half screen
w, h = root.winfo_screenwidth(), root.winfo_screenheight()
root.geometry("%dx%d+0+0" % (.5*w, .5*h))
root.title("NOSEpick")
root.config(bg="#d9d9d9")
img = tk.PhotoImage(file='lib/NosePick_ZOOM-01.png')
root.tk.call('wm', 'iconphoto', root._w, img)
# call the NOSEpickGUI class
gui.MainGUI(root, in_path, out_path, map_path)
root.mainloop()
