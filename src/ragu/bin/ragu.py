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
environment requirements in ragu.yml
"""
### imports ###
from ragu import config
from ragu.ui import gui
import os,sys,argparse
import tkinter as tk
from tkinter import font

def main():

    # get configuration file
    basedir = os.path.join(os.path.expanduser('~'),'RAGU')
    if not os.path.isdir(basedir):
        os.mkdir(basedir)
    if not os.path.isfile(basedir+'/config.ini'):
        config.create_config(basedir+'/config.ini')
    configPath = basedir + '/config.ini'

    # set up CLI
    parser = argparse.ArgumentParser(
    description=f"Radar Analysis Graphical Utility (RAGU)\n\nFor documentation see: https://github.com/btobers/RAGU\nDefulat configuration file path: {configPath}",
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument("datPath", help="Data directory file path", nargs="?", default=None)
    parser.add_argument("configPath", help="Configuration file path", nargs="?", default=configPath)
    datPath = parser.parse_args().datPath
    tmp = parser.parse_args().configPath

    # check if path exists
    if datPath:
        if not os.path.isdir(datPath[0]):
            print(f"Data directory not found : {datPath[0]}")
            print(f"Defaulting to data file path specified in the RAGU configuration file.")
            datPath = None
    if os.path.isfile(tmp) and tmp.endswith(".ini"):
        configPath=tmp
    else:
        print(f"Configuration file not found at: {tmp}\nFull file path must be entered.\nDefaulting to: {configPath}")

    # change dir to RAGU code directory 
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # initialize tkinter
    root = tk.Tk()

    # get screen size - open root window half screen
    w, h = root.winfo_screenwidth(), root.winfo_screenheight()
    root.geometry("%dx%d+0+0" % (.5*w, .5*h))
    root.title("RAGU")
    root.config(bg="#d9d9d9")
    try:
        for _i in tk.font.names():
            # tk.font.nametofont(_i).config(family="Times New Roman", size=10, weight="normal")
            tk.font.nametofont(_i).config(size=10, weight="normal")
    except:
        pass

    # call the RAGU mainGUI class
    gui.mainGUI(root, configPath=configPath, datPath=datPath)
    root.lift()    
    root.mainloop()

if __name__ == "__main__":
    main()