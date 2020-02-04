import utils
import numpy as np
from scipy.interpolate import CubicSpline
import tkinter as tk
import sys,os,time
import matplotlib as mpl
mpl.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import copy

class wvPick(tk.Frame):
    # wvPick is a class to optimize the picking of horizons from radar data
    def __init__(self, parent, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)
        self.parent = parent

        # set up frames
        infoFrame = tk.Frame(self.parent, highlightbackground="black", highlightthickness=1)
        infoFrame.pack(side="top",fill="both")
        toolbarFrame = tk.Frame(infoFrame)
        toolbarFrame.pack(side="bottom",fill="both")
        interpFrame = tk.Frame(toolbarFrame, highlightbackground="black", highlightthickness=1)
        interpFrame.pack(side="right",fill="both")
        self.dataFrame = tk.Frame(self.parent)
        self.dataFrame.pack(side="bottom", fill="both", expand=1)

        self.winSize = tk.IntVar(value=40)
        self.stepSize = tk.IntVar(value=10)
        self.segmentVar = tk.IntVar()
        self.segmentVar.trace('w', self.plot_wv)

        self.interpType = tk.StringVar()

        # infoFrame exists for options to be added based on optimization needs
        windowLabel = tk.Label(infoFrame, text = "window size [#samples]").pack(side="left")
        windowEntry = tk.Entry(infoFrame, textvariable=self.winSize, width = 5).pack(side="left")
        stepLabel = tk.Label(infoFrame, text = "\tstep size [#traces]").pack(side="left")
        stepEntry = tk.Entry(infoFrame, textvariable=self.stepSize, width = 5).pack(side="left")
        tk.Label(infoFrame, text="\t").pack(side="left")
        stepBackward = tk.Button(infoFrame, text="←", command = self.stepBackward, pady=0).pack(side="left")
        stepForward = tk.Button(infoFrame, text="→", command = self.stepForward, pady=0).pack(side="left")
        tk.Label(infoFrame, text="\t").pack(side="left")
        
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
        self.click = self.fig.canvas.mpl_connect("button_press_event", self.onpress)
        self.unclick = self.fig.canvas.mpl_connect('button_release_event', self.onrelease)

        # add toolbar to plot
        self.toolbar = NavigationToolbar2Tk(self.dataCanvas, toolbarFrame)
        self.toolbar.pack(side="left")
        # self.toolbar.update()

        interpButton = tk.Button(interpFrame, text="interpolate", command=self.interpPicks, pady=0).pack(side="right")
        autoButton = tk.Button(interpFrame, text="AutoPick", command=self.autoPick, pady=0).pack(side="right")
        linearRadio = tk.Radiobutton(interpFrame, text="linear", variable=self.interpType, value="linear")
        linearRadio.pack(side="right")
        sep = tk.ttk.Separator(interpFrame,orient="vertical")
        sep.pack(side="right", fill="y", padx=4, pady=4)
        cubicRadio = tk.Radiobutton(interpFrame,text="cubic spline", variable=self.interpType, value="cubic")
        cubicRadio.pack(side="right")


        # create the figure axes
        self.ax = self.fig.add_subplot(111)
        self.ax.set_visible(False)

        # update the canvas
        self.dataCanvas._tkcanvas.pack()
        self.dataCanvas.draw()
    

    def set_vars(self):
        # set up variables
        self.trace = 0.
        self.pick_dict0 = {}
        self.pick_dict1 = {}
        self.rePick = None
        self.rePick_idx = {}        # dictionary of indeces of repicked traces for each segment
        self.interpType.set("cubic")


    # set_data is a method to receive the radar data
    def set_data(self, amp, dt, num_sample):
        self.data_amp = amp
        self.dt = dt
        self.num_sample = num_sample
        # self.data_dB = 20*np.log10(amp)
        self.data_dB = np.log(np.power(amp,2))
        self.sampleTime = np.arange(0,self.num_sample+1)*self.dt


    # get_pickDict is a method to return the pick dictionary
    def get_pickDict(self):
        return dict(self.pick_dict1)


    # set_pickDict is a method which holds the picked segment data for optimization
    def set_pickDict(self, pickDict):
        # create a copy of pick_dict passed from imPick as to not modify original values
        self.pick_dict0 = pickDict
        self.pick_dict1 = copy.deepcopy(pickDict)

        # determine number of pick segments
        self.num_pkLyrs = len(self.pick_dict0)
        self.ax.set_visible(True)
        self.update_option_menu()

        # create lists of first and last picked trace number for each segment
        self.segment_trace_first = []
        self.segment_trace_last = []
        # create list to hold current trace number for each layer
        self.traceNum = []
        for _i in range(self.num_pkLyrs):
            picked_traces = np.where(self.pick_dict0["segment_" + str(_i)] != -1.)[0]
            self.segment_trace_first.append(picked_traces[0])
            self.segment_trace_last.append(picked_traces[-1])
            self.traceNum.append(np.where(self.pick_dict0["segment_" + str(_i)] != -1.)[0][0])


    # plot_wv is a method to draw the waveform on the datacanvas
    def plot_wv(self, *args):
        # if self.pick_dict1:
        self.ax.clear()
        self.ax.set(xlabel = "sample", ylabel = "decibels")
        # self.segment = str(self.segmentVar.get())

        # print(np.where(self.pick_dict1["segment_" + self.segment] != -1.))
        # print(np.where(self.pick_dict1["segment_" + self.segment] != -1.)[0])
        # traceNum = np.where(self.pick_dict1["segment_" + self.segment] != -1.)[0][self.segment_trace]
        # print(traceNum)

        # get sample index of pick for given trace
        pick_idx0 = utils.find_nearest(self.sampleTime, (self.pick_dict0["segment_" + str(self.segmentVar.get())][self.traceNum[self.segmentVar.get()]]*1e-6))
        pick_idx1 = utils.find_nearest(self.sampleTime, (self.pick_dict1["segment_" + str(self.segmentVar.get())][self.traceNum[self.segmentVar.get()]]*1e-6))

        self.ax.plot(self.data_dB[:,self.traceNum[self.segmentVar.get()]])
        pick_0 = self.ax.axvline(x = pick_idx0, c="k", label="Initial Pick")

        if pick_idx0 != pick_idx1:
            pick_1 = self.ax.axvline(x = pick_idx1, c="g", ls = "--", label="Updated Pick")
        
        # save un-zoomed view to toolbar
        self.toolbar.push_current()

        # zoom in
        winSize = self.winSize.get()
        self.ax.set(xlim=(int(pick_idx0-(winSize/2)),int(pick_idx0+(winSize/2))))

        self.ax.legend()

        self.dataCanvas.draw()


    # step forward is a method to move backwards by the number of traces entered to stepSize
    def stepBackward(self):
        if self.pick_dict1 and self.traceNum[self.segmentVar.get()] - self.stepSize.get() >= self.segment_trace_first[self.segmentVar.get()]:
            self.traceNum[self.segmentVar.get()] -= self.stepSize.get()
            self.plot_wv()


    # step forward is a method to move forward by the number of traces entered to stepSize
    def stepForward(self):
        newTrace = self.traceNum[self.segmentVar.get()] + self.stepSize.get()
        lastTrace_seg = self.segment_trace_last[self.segmentVar.get()]
        if self.pick_dict1 and newTrace <= lastTrace_seg:
            self.traceNum[self.segmentVar.get()] += self.stepSize.get()
        # if there are less traces left in the pick segment than the step size, move to the last trace in the segment
        elif self.pick_dict1 and newTrace > lastTrace_seg:
            if self.traceNum[self.segmentVar.get()] == lastTrace_seg:
                if self.segmentVar.get() + 2 <= self.num_pkLyrs and tk.messagebox.askokcancel("Next Sement?","Finished optimization of current pick segment\n\tProceed to next segment?") == True:
                    self.segmentVar.set(self.segmentVar.get() + 1) 
            else:
                self.traceNum[self.segmentVar.get()] = self.segment_trace_last[self.segmentVar.get()]
       
        self.plot_wv()


    # update the pick segment menu based on how many segments exist
    def update_option_menu(self):
            menu = self.segmentMenu["menu"]
            menu.delete(0, "end")
            for _i in range(self.num_pkLyrs):
                menu.add_command(label=_i, command=tk._setit(self.segmentVar,_i))
                self.rePick_idx["segment_" + str(_i)] = []


    # autoPick is a method to automatically optimize picks
    def autoPick(self):
        print('-----------\nauto pick still in development\n-----------')
        # for _i in range(self.num_pkLyrs):
        #     x = np.where(self.pick_dict0["segment_" + str(_i)] != -1)[0]
        #     self.pick_dict1["segment_" + str(_i)][x] = self.sampleTime[np.argmax(self.data_amp)]


    def manualPick(self, event):
        if (not self.pick_dict0) or (event.inaxes != self.ax):
            return

        # append trace number to rePick_idx list to keep track of indeces for interpolation
        if (len(self.rePick_idx["segment_" + str(self.segmentVar.get())]) == 0) or (self.rePick_idx["segment_" + str(self.segmentVar.get())][-1] != self.traceNum[self.segmentVar.get()]):
            self.rePick_idx["segment_" + str(self.segmentVar.get())].append(self.traceNum[self.segmentVar.get()])
        
        self.pick_dict1["segment_" + str(self.segmentVar.get())][self.traceNum[self.segmentVar.get()]] = event.xdata*self.dt*1e6

        self.plot_wv()

    # interpPicks is a method to interpolate linearly between refined picks
    def interpPicks(self):
        print('-----------\nwave pick interpolation still in development\n-----------')
        if self.interpType.get() == "linear":
            for _i in range(self.num_pkLyrs):
                if len(self.rePick_idx["segment_" + str(_i)]) >= 2:
                    # get indices where picks exist for pick segment
                    x = np.where(self.pick_dict1["segment_" + str(_i)] != -1)[0]
                    # get indeces of repicked traces
                    xp = self.rePick_idx["segment_" + str(_i)]
                    # get twtt values at repicked indices
                    fp = self.pick_dict1["segment_" + str(_i)][xp]
                    # interpolate repicked values for segment
                    self.pick_dict1["segment_" + str(_i)][x] = np.interp(x, xp, fp)            


        elif self.interpType.get() == "cubic":
            for _i in range(self.num_pkLyrs):
                if len(self.rePick_idx["segment_" + str(_i)]) >= 2:
                    # cubic spline between picks
                    rePick_idx = self.rePick_idx["segment_" + str(_i)]
                    cs = CubicSpline(rePick_idx, self.pick_dict1["segment_" + str(_i)][rePick_idx])
                    # generate array between first and last pick indices on current layer
                    interp_idx = np.where(self.pick_dict1["segment_" + str(_i)] != -1.)[0]
                    # add cubic spline output interpolation to pick dictionary
                    self.pick_dict1["segment_" + str(_i)][interp_idx] = cs([interp_idx])

                    plt.plot(self.pick_dict0["segment_0"][interp_idx])
                    plt.plot(self.pick_dict1["segment_0"][interp_idx])
                    plt.show()


    # onpress gets the time of the button_press_event
    def onpress(self,event):
        self.time_onclick = time.time()


    # onrelease calls addseg() if the time between the button press and release events
    # is below a threshold so that segments aren't drawn while trying to zoom or pan
    def onrelease(self,event):
        if event.inaxes == self.ax:
            if event.button == 1 and ((time.time() - self.time_onclick) < 0.25):
                self.manualPick(event)


    # clear is a method to clear the wavePick tab and stored data when a new track is loaded
    def clear(self):
        self.ax.clear()
        self.dataCanvas.draw()