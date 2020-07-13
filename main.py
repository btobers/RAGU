"""
NOSEpick - Nearly Optimal Subsurface Extractor
created by: Brandon S. Tober and Michael S. Christoffersen
date: 25JUN19
last updated: 08JUL2020
environment requirements in nose_env.yml
"""

### IMPORTS ###
import os,sys
from config import *
import gui
import tkinter as tk
from tkinter import font

# allow for optional data directory input
if len(sys.argv) > 0:
    in_path = sys.argv[1]

# change dir to NOSEpick code directory 
os.chdir(os.path.dirname(os.path.abspath(__file__)))

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
gui.MainGUI(root, in_path, map_path, out_path, eps_r)
root.mainloop()