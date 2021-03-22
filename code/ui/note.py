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


class note(tk.Frame):
    def __init__(self, parent, init_dir):
        self.parent = parent
        self.init_dir = init_dir
        self.note_state = 0


    # setup the tkinter window
    def setup(self):
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

        self.note_window.rowconfigure(0, minsize=800, weight=1)
        self.note_window.columnconfigure(1, minsize=800, weight=1)
        self.txt_edit = tk.Text(self.note_window)
        self.txt_edit.pack(side="top")
        fr_buttons = tk.Frame(self.note_window)
        btn_open = tk.Button(fr_buttons, text="Open", command=self.open_file)
        btn_save = tk.Button(fr_buttons, text="Save", command=self.save_file)
        btn_open.pack(side="left")
        btn_save.pack(side="left")
        fr_buttons.pack(side="bottom")
        self.set_state(1)


    # open_file
    def open_file(self):
        filepath = tk.filedialog.askopenfilename(initialdir=self.init_dir,
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        if not filepath:
            return
        self.txt_edit.delete(1.0, tk.END)
        with open(filepath, "r") as input_file:
            text = input_file.read()
            self.txt_edit.insert(tk.END, text)
        self.note_window.title(filepath.split("/")[-1])


    # save_file
    def save_file(self):
        filepath = tk.filedialog.asksaveasfilename(initialdir=self.init_dir,
            defaultextension="txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
        )
        if not filepath:
            return
        with open(filepath, "w") as output_file:
            text = self.get_text()
            output_file.write(text)
        self.note_window.title(filepath.split("/")[-1])


    # write_track adds the current track from gui to a new line
    def write_track(self, fn=None):
        if fn:
            text = self.get_text()
            if fn in text:
                self.search_text(fn)
            else:
                if len(text) > 1:
                    fn = "\n" + fn
                self.txt_edit.insert(tk.END, fn + ",")
                self.txt_edit.see("insert")


    # get_text returns the text entry string
    def get_text(self):
        return self.txt_edit.get(1.0, tk.END)


    # note_close is a method to close the note window
    def note_close(self, event=None):
        self.note_window.destroy()
        self.set_state(0)


    # get_state is a mathod to get the note state
    def get_state(self):
        return self.note_state


    # set_state is a mathod to update the note state
    def set_state(self, state=0):
        self.note_state = state

    
    # search_text
    def search_text(self, lookup):
        for num, line in enumerate(self.get_text().splitlines()):
            if lookup in line:
                self.txt_edit.mark_set("insert", str(num) + "." + str(len(line)))
                self.txt_edit.see("insert")