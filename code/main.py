# RAGU - Radar Analysis Graphical Utility
#
# copyright © 2020 btobers <tobers.brandon@gmail.com>
#
# distributed under terms of the GNU GPL3.0 license
"""
RAGU - Radar Analysis Graphical Utility
created by: Brandon S. Tober and Michael S. Christoffersen
date: 25JUN19
last updated: 08JUL2020
environment requirements in ragu_env.yml
"""
### imports ###
import os,sys,configparser
from ui import gui
import tkinter as tk
from tkinter import font

def main():
    # allow for optional data directory input
    if len(sys.argv) > 1:
        datPath = sys.argv[1]
    else:
        datPath = None

    # change dir to RAGU code directory 
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # initialize tkinter
    root = tk.Tk()

    # get screen size - open root window half screen
    w, h = root.winfo_screenwidth(), root.winfo_screenheight()
    root.geometry("%dx%d+0+0" % (.5*w, .75*h))
    root.title("RAGU")
    root.config(bg="#d9d9d9")
    for _i in tk.font.names():
        tk.font.nametofont(_i).config(family="Times New Roman", size=12, weight="normal")
    # img = tk.PhotoImage(file='../recs/NOSEpick_zoom.png')
    # root.tk.call('wm', 'iconphoto', root._w, img)
    # call the RAGU mainGUI class
    gui.mainGUI(root, datPath = datPath)
    root.mainloop()

if __name__ == "__main__":
    main()