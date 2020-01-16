import utils
import numpy as np
import tkinter as tk
import sys,os,time
import matplotlib as mpl
mpl.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

class wvPick(tk.Frame):
    # wvPick is a class to optimize the picking of horizons from radar data
    def __init__(self, parent, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)
        self.parent = parent

    def setup(self):
        # set up frames
        infoFrame = tk.Frame(self.parent)
        infoFrame.pack(side="top",fill="both")
        toolbarFrame = tk.Frame(infoFrame)
        toolbarFrame.pack(side="bottom",fill="both")
        self.dataFrame = tk.Frame(self.parent)
        self.dataFrame.pack(side="bottom", fill="both", expand=1)

        # infoFrame exists for options to be added based on optimization needs
        windowLabel = tk.Label(infoFrame, text = "window size [#samples]").pack(side="left")
        windowEntry = tk.Entry(infoFrame, textvariable=self.winSize, width = 5).pack(side="left")
        stepLabel = tk.Label(infoFrame, text = "\tstep size [#traces]").pack(side="left")
        stepEntry = tk.Entry(infoFrame, textvariable=self.stepSize, width = 5).pack(side="left")
        tk.Label(infoFrame, text="\t").pack(side="left")
        stepBackward = tk.Button(infoFrame, text="←", command = self.stepBackward, pady=0).pack(side="left")
        stepForward = tk.Button(infoFrame, text="→", command = self.stepForward, pady=0).pack(side="left")
        tk.Label(infoFrame, text="\t").pack(side="left")
        interpButton = tk.Button(infoFrame, text="Interpolate", command=self.interpPicks, pady=0).pack(side="left")
        tk.Label(infoFrame, text="\t").pack(side="left")
        autoButton = tk.Button(infoFrame, text="AutoPick", command=self.autoPick, pady=0).pack(side="left")
        
        self.segments=[0]
        self.segmentMenu = tk.OptionMenu(infoFrame, self.segmentVar, *self.segments)
        self.segmentMenu.pack(side="right",pady=0)
        self.segmentMenu["highlightthickness"]=0
        segmentLabel = tk.Label(infoFrame, text = "subsurface pick segment").pack(side="right")

        # create figure object and datacanvas from it
        self.fig = mpl.figure.Figure()
        self.fig.patch.set_facecolor("#d9d9d9")
        self.dataCanvas = FigureCanvasTkAgg(self.fig, self.parent)
        self.dataCanvas.get_tk_widget().pack(in_=self.dataFrame, side="bottom", fill="both", expand=1) 
        self.click = self.fig.canvas.mpl_connect("button_press_event", self.manualPick)
        
        # add toolbar to plot
        self.toolbar = NavigationToolbar2Tk(self.dataCanvas, toolbarFrame)
        self.toolbar.update()

        # create the figure axes
        self.ax = self.fig.add_subplot(111)
        self.ax.set_visible(False)
        self.ax.set_title('decibels')

        # update the canvas
        self.dataCanvas._tkcanvas.pack()
        self.dataCanvas.draw()
    
    def set_vars(self):
        # set up variables
        self.winSize = tk.IntVar(value=20)
        self.stepSize = tk.IntVar(value=50)
        self.segmentVar = tk.IntVar()
        self.segmentVar.trace('w', self.plot_wv)
        self.trace = 0.
        self.pick_dict = None
        self.rePick = None
        self.rePick_idx = {}        # dictionary of indeces of repicked traces for each segment
        self.pick_idx0 = []         # list of start index for each pick segment

    # set_data is a method to receive the radar data
    def set_data(self, amp, dt, num_sample):
        self.data_amp = amp
        self.dt = dt
        self.num_sample = num_sample
        # self.data_dB = 20*np.log10(amp)
        self.data_dB = np.log(np.power(amp,2))
        self.sampleTime = np.arange(0,self.num_sample+1)*self.dt


    # set_pickDict is a method which holds the picked segment data for optimization
    def set_pickDict(self, pickDict):
        self.pick_dict = pickDict
        # determine number of pick segments
        self.num_pkLyrs = len(self.pick_dict)
        self.ax.set_visible(True)
        self.update_option_menu()

        # create lists of first and last picked trace number for each segment
        self.segment_trace_first = []
        self.segment_trace_last = []
        for _i in range(self.num_pkLyrs):
            picked_traces = np.where(self.pick_dict["segment_" + str(_i)] != -1.)[0]
            self.segment_trace_first.append(picked_traces[0])
            self.segment_trace_last.append(picked_traces[-1])
        self.traceNum = np.where(self.pick_dict["segment_" + str(self.segmentVar.get())] != -1.)[0][0]


    # plot_wv is a method to draw the waveform on the datacanvas
    def plot_wv(self, *args):
        if self.pick_dict:
            self.ax.clear()
            # self.segment = str(self.segmentVar.get())

            # print(np.where(self.pick_dict["segment_" + self.segment] != -1.))
            # print(np.where(self.pick_dict["segment_" + self.segment] != -1.)[0])
            # traceNum = np.where(self.pick_dict["segment_" + self.segment] != -1.)[0][self.segment_trace]
            # print(traceNum)

            # get sample index of pick for given trace
            pick_idx = utils.find_nearest(self.sampleTime, (self.pick_dict["segment_" + str(self.segmentVar.get())][self.traceNum]*1e-6))

            self.ax.plot(self.data_dB[:,self.traceNum])
            self.ax.axvline(x = pick_idx, color='r')

            self.ax.axis(xmin=int(pick_idx-100),xmax=int(pick_idx+100))

            self.dataCanvas.draw()

    # step forward is a method to move backwards by the number of traces entered to stepSize
    def stepBackward(self):
        if self.pick_dict and self.traceNum - self.stepSize.get() >= self.segment_trace_first[self.segmentVar.get()]:
            self.traceNum -= self.stepSize.get()
            self.plot_wv()

    # step forward is a method to move forward by the number of traces entered to stepSize
    def stepForward(self):
        if self.pick_dict and self.traceNum + self.stepSize.get() <= self.segment_trace_last[self.segmentVar.get()]:
            self.traceNum += self.stepSize.get()
            self.plot_wv()


    # update the pick segment menu based on how many segments exist
    def update_option_menu(self):
            menu = self.segmentMenu["menu"]
            menu.delete(0, "end")
            for _i in range(self.num_pkLyrs):
                menu.add_command(label=_i,
                    command=tk._setit(self.segmentVar,_i))
                self.rePick_idx["segment_" + str(_i)] = []
                self.pick_idx0.append(np.where(self.pick_dict["segment_" + str(_i)] != -1.)[0][0])


    def autoPick(self):
        print('-----------\nauto pick still in development\n-----------')


    def manualPick(self, event):
        if (not self.pick_dict) or (event.inaxes != self.ax):
            return
        if self.rePick:
            self.rePick.remove()
        self.rePick = self.ax.axvline(x=event.xdata, c='g')
        self.dataCanvas.draw()

        # append trace number to rePick_idx list to keep track of indeces for interpolation
        if (len(self.rePick_idx["segment_" + str(self.segmentVar.get())]) == 0) or (self.rePick_idx["segment_" + str(self.segmentVar.get())][-1] != self.segment_trace):
            self.rePick_idx["segment_" + str(self.segmentVar.get())].append(self.traceNum)

        self.pick_dict["segment_" + self.segment][self.pick_idx0[self.segmentVar.get()] + self.traceNum] = round(event.xdata)*self.dt*1e6


    # interpPicks is a method to interpolate linearly between refined picks
    def interpPicks(self):
        print('-----------\nwave pick interpolation still in development\n-----------')
        # for _i in range(len(self.rePick_idx)):
        #     if len(self.rePick_idx["segment_" + str(_i)]) >= 2:
        #         # get indices where picks exist for pick segment
        #         x = np.where(self.pick_dict["segment_" + str(_i)] != -1)[0]
        #         # get indeces of repicked traces
        #         xp = self.pick_idx0[_i] + self.rePick_idx["segment_" + str(_i)]
        #         # get twtt values at repicked indices
        #         fp = self.pick_dict["segment_" + str(_i)][xp]
        #         # interpolate repicked values for segment
        #         self.pick_dict["segment_" + str(_i)][x] = np.interp(x, xp, fp)            

    # clear is a method to clear the wavePick tab and stored data when a new track is loaded
    def clear(self):
