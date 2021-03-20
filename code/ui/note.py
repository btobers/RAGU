# RAGU - Radar Analysis Graphical Utility
#
# copyright © 2020 btobers <tobers.brandon@gmail.com>
#
# distributed under terms of the GNU GPL3.0 license
"""
note class is a tkinter frame which handles the RAGU session notes
"""
### imports ###
import tkinter as tk
import os, pyproj, glob

import tkinter as tk
from tkinter.filedialog import askopenfilename, asksaveasfilename

def open_file():
    """Open a file for editing."""
    filepath = askopenfilename(
        filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
    )
    if not filepath:
        return
    txt_edit.delete(1.0, tk.END)
    with open(filepath, "r") as input_file:
        text = input_file.read()
        txt_edit.insert(tk.END, text)
    window.title(f"Text Editor Application - {filepath}")

def save_file():
    """Save the current file as a new file."""
    filepath = asksaveasfilename(
        defaultextension="txt",
        filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
    )
    if not filepath:
        return
    with open(filepath, "w") as output_file:
        text = txt_edit.get(1.0, tk.END)
        output_file.write(text)
    window.title(f"Text Editor Application - {filepath}")

window = tk.Tk()
window.title("Text Editor Application")
window.rowconfigure(0, minsize=800, weight=1)
window.columnconfigure(1, minsize=800, weight=1)

txt_edit = tk.Text(window)
fr_buttons = tk.Frame(window, relief=tk.RAISED, bd=2)
btn_open = tk.Button(fr_buttons, text="Open", command=open_file)
btn_save = tk.Button(fr_buttons, text="Save As...", command=save_file)

btn_open.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
btn_save.grid(row=1, column=0, sticky="ew", padx=5)

fr_buttons.grid(row=0, column=0, sticky="ns")
txt_edit.grid(row=0, column=1, sticky="nsew")

window.mainloop()





class note(tk.Frame):
    def __init__(self, parent, datPath, navcrs, body, to_gui):
        self.parent = parent
        self.datPath = datPath
        self.to_gui = to_gui
        # create tkinter toplevel window to display note
        self.note_window = tk.Toplevel(self.parent)
        # img = tk.PhotoImage(file="../recs/note_icon.png")
        # self.note_window.tk.call("wm", "iconphoto", self.note_window._w, img)
        self.note_window.config(bg="#d9d9d9")
        self.note_window.title("RAGU - Session Notes")
        self.map_display = tk.Frame(self.note_window)
        self.map_display.pack(side="bottom", fill="both", expand=1)
        # bind ctrl-q key to note_close()
        self.note_window.bind("<Control-q>", self.note_close)
        # bind x-out to note_close()
        self.note_window.protocol("WM_DELETE_WINDOW", self.note_close)
        self.cmap = tk.StringVar(value="Greys_r")
        self.setup()


    # setup the tkinter window
    def setup(self):
        # show note figure in note window
        # generate menubar
        menubar = tk.Menu(self.note_window)
        fileMenu = tk.Menu(menubar, tearoff=0)

        # settings submenu
        loadMenu = tk.Menu(fileMenu,tearoff=0)
        loadMenu.add_command(label="select files", command=self.load_tracks)
        loadMenu.add_command(label="select folder", command= lambda: self.load_tracks(dir = True))
        fileMenu.add_cascade(label="load tracks", menu = loadMenu)

        fileMenu.add_command(label="clear tracks", command=self.clear_nav)
        fileMenu.add_command(label="preferences", command=self.settings)
        fileMenu.add_command(label="exit       [ctrl+q]", command=self.note_close)
        # add items to menubar
        menubar.add_cascade(label="file", menu=fileMenu)
        # add the menubar to the window
        self.note_window.config(menu=menubar)

        # set up info frame
        infoFrame = tk.Frame(self.note_window)
        infoFrame.pack(side="top",fill="both")
        # button to toggle track visibility
        self.track_viz = tk.BooleanVar(value=True)
        tk.Label(infoFrame, text="track display: ").pack(side="left")
        tk.Radiobutton(infoFrame,text="all", variable=self.track_viz, value=True, command=self.plot_tracks).pack(side="left")
        tk.Radiobutton(infoFrame,text="current", variable=self.track_viz, value=False, command=self.plot_tracks).pack(side="left")

        # initialize the note figure
        self.map_fig = mpl.figure.Figure()
        self.map_fig.patch.set_facecolor(self.parent.cget("bg"))
        self.map_fig_ax = self.map_fig.add_subplot(111)
        self.bm_im = self.map_fig_ax.imshow(np.ones((100,100)), cmap=self.cmap.get(), aspect="auto")
        self.map_fig_ax.set_visible(False)
        self.map_fig_ax.set(xlabel = "x [km]", ylabel = "y [km]")
        # initialize artists
        self.track_ln, = self.map_fig_ax.plot([], [], "k.", ms=.1, picker=True)
        self.track_start_ln, = self.map_fig_ax.plot([], [], "go", ms=3, label="start")
        self.track_end_ln, = self.map_fig_ax.plot([], [], "ro", ms=3, label="end")
        # pack mpl figure in canvas window
        self.map_dataCanvas = FigureCanvasTkAgg(self.map_fig, self.note_window)
        self.map_dataCanvas.get_tk_widget().pack(in_=self.map_display, side="bottom", fill="both", expand=1)
        self.map_toolbar = NavigationToolbar2Tk(self.map_dataCanvas, self.note_window)
        self.map_dataCanvas._tkcanvas.pack()
        self.note_state = 1
        self.draw_cid = self.map_fig.canvas.mpl_connect("draw_event", self.update_bg)
        self.pick_cid = self.map_fig.canvas.mpl_connect("pick_event", self.on_pick)


    def set_vars(self):
        # initialize arrays to hold track nav info
        self.x = np.array(())
        self.y = np.array(())
        self.track_name = np.array(()).astype(dtype=np.str)
        self.loaded_tracks = np.array(()).astype(dtype=np.str)
        self.start_x = np.array(())
        self.start_y = np.array(())
        self.end_x = np.array(())
        self.end_y = np.array(())
        self.legend = None
        self.pick_loc = None
        self.profile_track = None

    # note_close is a method to close the note window
    def note_close(self, event=None):
        self.note_window.destroy()
        self.note_state = 0


    # get_state is a mathod to get the note state
    def get_state(self):
        return self.note_state