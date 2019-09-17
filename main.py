"""
NOSEpick - currently in development stages
created by: Brandon S. Tober and Michael S. Christoffersen
date: 25JUN19
last updated: 05SEP19
environment requirements in nose_env.yml
"""

### IMPORTS ###
import gui
import tkinter as tk

### USER SPECIFIED VARS ###
in_path = "/mnt/Swaps/MARS/targ/supl/UAF/2018/aug/export"
map_path = "/mnt/Swaps/MARS/targ/supl/grid-AKDEM/"

### INITIALIZE ###
root = tk.Tk()
# get screen size - open root window half screen
w, h = root.winfo_screenwidth(), root.winfo_screenheight()
root.geometry("%dx%d+0+0" % (.5*w, .5*h))
root.title("NOSEpick")
# img = tk.PhotoImage(file='nose-pick-icon.png')
# root.tk.call('wm', 'iconphoto', root._w, img)
# call the NOSEpickGUI class
gui = gui.MainGUI(root, in_path, map_path)
root.mainloop()