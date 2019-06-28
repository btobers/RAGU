'''script to run NOSEpick - currently in development stages
created by: Brandon S. Tober
date:25JUN19

dependencies: 
python 3
h5py
numpy
matplotlib
pytables
'''


# import necessary libraries
import sys
import functions.run as run
import scipy
import numpy as np
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
try:
    import Tkinter as tk
except:
    import tkinter as tk
from tkinter import ttk
from tkinter import messagebox as msg

in_path = '/home/anomalocaris/Desktop/tmp/20180819-215243.mat'

name = in_path.split('/')[-1].rstrip('.mat')

amp, dist, dt = run.ingest(in_path)
amp = np.transpose(amp)


# run.rgram(amp, dist, dt, name)

class Root(tk.Tk):

    def __init__(self):
        super(Root, self).__init__()
        self.title("NOSEpick")
        # self.minsize(800, 800)
        self.button()
        self.matplotCanvas(amp, dist, dt)
        self.bind("<Button-1>", self.on_click)
        # self.bind("<Key-c>", self.clear_canvas)

    def matplotCanvas(self, amp, dist, dt):

        # create matplotlib figure and use imshow to display radargram
        f = Figure()
        a = f.add_subplot(111)
        a.imshow(np.log(np.power(amp,2)), cmap='gray', aspect='auto', extent=[dist[0], dist[-1], amp.shape[0] * dt * 1e6, 0])
        a.set_title(name)
        a.set(xlabel = 'along-track distance [km]', ylabel = 'two-way travel time [microsec.]')

        # create the canvas widget
        canvas = FigureCanvasTkAgg(f, self)
        canvas.draw()
        canvas.get_tk_widget().pack(side="top", fill="both", expand=1)

        # create exit button to close window
        button = tk.Button(text = "Exit", fg = "red", command = self.close_window)
        button.pack(side="right")

        # add matplotlib figure nav toolbar
        toolbar = NavigationToolbar2Tk(canvas, self)
        toolbar.update()
        canvas._tkcanvas.pack(side="top", fill="both", expand=1)

    def button(self):

        # create instructions button
        self.btn = ttk.Button(self, text = "Instructions", command = self.mssgBox)
        self.btn.pack(side="top")
    
    def mssgBox(self):

        # instructions button message box
        msg.showinfo("NOSEpick Instructions", "Nearly Optimal Subsurface Extractor:\n\nClick along reflector surface\n<spacebar> to remove the last pick\n<c> to remove all picks")

    def close_window(self):

        # destroy canvas upon Exit button click
        self.destroy()

    #####################
    #  WORKING INDEPENDENTLY, but not yet incorporated properly
    line = []
    def on_click(self, event):
        global line
        if len(self.line) == 0:
            # define line starting point
            self.line=[event.x, event.y]
            print(self.line)

        elif len(self.line) >=  2:
            # starting point has been defined
            self.line.extend([event.x, event.y])
            print(self.line)
            self.canvas.create_line(*self.line,fill="red",width=2)

    def remove_last(self, event):
        global line
        if len(self.line) > 0:
            del self.line[-2:]
            self.canvas.delete('all')
            if len(self.line) >= 4:
                self.canvas.create_line(*self.line,fill="red",width=2)

    # def clear_canvas(self, event):
    #     global line
    #     self.canvas.delete('all')
    #     self.line = []
    #######################
root = Root()
root.mainloop()

















# root = tk.Tk()
# app = NOSEpick(master=root)
# app.mainloop()

# def close_window ():
#     root.destroy()


# root = tk.Tk()
# root.wm_title("NOSEpick")
# # root_panel = tk.Frame(root)

# f = Figure()
# a = f.add_subplot(111)

# a.imshow(np.log(np.power(amp,2)), cmap='gray', aspect='auto', extent=[dist[0], dist[-1], amp.shape[0] * dt * 1e6, 0])
# a.set_title(name)
# a.set(xlabel = 'along-track distance [km]', ylabel = 'two-way travel time [microsec.]')

# canvas = FigureCanvasTkAgg(f, master=root)
# canvas.draw()
# canvas.get_tk_widget().pack(side="top", fill="both", expand=1)
# canvas._tkcanvas.pack(side="top", fill="both", expand=1)

# button = tk.Button(text = "Exit", fg = "red", command = close_window)
# button.pack(side="right")

# toolbar = NavigationToolbar2Tk(canvas,root)
# canvas._tkcanvas.pack(side="top", fill="both", expand=1)



# root.mainloop()