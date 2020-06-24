"""
NOSEpick - Nearly Optimal Subsurface Extractor
created by: Brandon S. Tober and Michael S. Christoffersen
date: 25JUN19
last updated: 29FEB20
environment requirements in nose_env.yml
"""

### IMPORTS ###
import gui
import tkinter as tk
from tkinter import font
import os

### USER SPECIFIED VARS ###

# relative paths
# in_path = "/media/btober/beefmaster/MARS/targ/supl/UAF/2019/hdf5/"
in_path = "/home/btober/Documents/"
map_path = "/home/btober/Documents/OIB-AK_qgis/"
# NOSEpick code path
os.chdir("/home/btober/Documents/NOSEpick/")

### INITIALIZE ###
root = tk.Tk()

# get screen size - open root window half screen
w, h = root.winfo_screenwidth(), root.winfo_screenheight()
root.geometry("%dx%d+0+0" % (.5*w, .5*h))
root.title("NOSEpick")
root.config(bg="#d9d9d9")
img = tk.PhotoImage(file='lib/NOSEpick_zoom.png')
root.tk.call('wm', 'iconphoto', root._w, img)
# call the NOSEpickGUI class
gui.MainGUI(root, in_path, map_path)
root.mainloop()