"""
NOSEpick - currently in development stages
created by: Brandon S. Tober and Michael S. Christoffersen
date: 25JUN19
last updated: 19SEP2019
environment requirements in nose_env.yml
"""

### IMPORTS ###
import gui
import tkinter as tk

### USER SPECIFIED VARS ###
in_path = "/mnt/Swaps/MARS/targ/supl/UAF/2018/may/block_clutter_elev"
out_path = "/home/anomalocaris/Desktop"
map_path = "/mnt/Swaps/MARS/targ/supl/grid-AKDEM/"

### INITIALIZE ###
root = tk.Tk()
# get screen size - open root window half screen
w, h = root.winfo_screenwidth(), root.winfo_screenheight()
root.geometry("%dx%d+0+0" % (w, h))
root.title("NOSEpick")
root.config(bg="#d9d9d9")
# img = tk.PhotoImage(file='nose-pick-icon.png')
# root.tk.call('wm', 'iconphoto', root._w, img)
# call the NOSEpickGUI class
gui.MainGUI(root, in_path, out_path, map_path)
root.mainloop()