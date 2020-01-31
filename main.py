"""
NOSEpick - Nearly Optimal Subsurface Extractor
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

# anomalocaris paths
in_path = "/mnt/Swaps/MARS/targ/supl/UAF/2017/aug/block_clutter_pc"
map_path = "/mnt/Swaps/MARS/targ/supl/grid-AKDEM/"

# # colugo paths
# in_path = "/zippy/MARS/targ/supl/UAF/2017/aug/"
# map_path = "/zippy/MARS/targ/supl/grid-AKDEM/"

# beefmaser paths
# in_path = "/media/anomalocaris/beefmaster/MARS/targ/supl/UAF/2019/hdf5/"
# map_path = "/media/anomalocaris/beefmaster/MARS/targ/supl/grid-AKDEM/"

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
gui.MainGUI(root, in_path, map_path)
root.mainloop()