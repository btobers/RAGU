# RAGU - Radar Analysis Graphical Utility
#
# copyright © 2020 btobers <tobers.brandon@gmail.com>
#
# distributed under terms of the GNU GPL3.0 license
"""
notepad class is a tkinter frame which handles the RAGU session notes
"""

import tkinter as tk
import os
  
class notepad(tk.Frame):

    # default window width and height 
    __thisWidth = 300
    __thisHeight = 300      
    __file = None

    def __init__(self, parent, init_dir, **kwargs):

        self.__parent = parent
        self.__init_dir = init_dir
        self.__state = 0
        try: 
            self.__thisWidth = kwargs['width'] 
        except KeyError: 
            pass
  
        try: 
            self.__thisHeight = kwargs['height'] 
        except KeyError: 
            pass
    
    def setup(self):
        # create tkinter toplevel window to display note
        self.__root = tk.Toplevel(self.__parent)
        self.__root.config(bg="#d9d9d9")
        self.__root.title("RAGU - Session Notes")
        self.__root.bind("<Control-q>", self.__quit)
        self.__root.protocol("WM_DELETE_WINDOW", self.__quit)
        self.__thisMenuBar = tk.Menu(self.__root) 
        self.__thisFileMenu = tk.Menu(self.__thisMenuBar, tearoff=0) 
        self.__thisEditMenu = tk.Menu(self.__thisMenuBar, tearoff=0) 
        self.__thisHelpMenu = tk.Menu(self.__thisMenuBar, tearoff=0) 
        self.__thisTextArea = tk.Text(self.__root) 
        self.__thisScrollBar = tk.Scrollbar(self.__thisTextArea)

        # Center the window 
        screenWidth = self.__root.winfo_screenwidth() 
        screenHeight = self.__root.winfo_screenheight() 
      
        # For left-alling 
        left = (screenWidth / 2) - (self.__thisWidth / 2)  
          
        # For right-allign 
        top = (screenHeight / 2) - (self.__thisHeight /2)  
          
        # For top and bottom 
        self.__root.geometry('%dx%d+%d+%d' % (self.__thisWidth, 
                                              self.__thisHeight, 
                                              left, top))  
  
        # To make the textarea auto resizable 
        self.__root.grid_rowconfigure(0, weight=1) 
        self.__root.grid_columnconfigure(0, weight=1) 
  
        # Add controls (widget) 
        self.__thisTextArea.grid(sticky = tk.N + tk.E + tk.S + tk.W) 
          
        # To open new file 
        self.__thisFileMenu.add_command(label="New", 
                                        command=self.__newFile)     
          
        # To open a already existing file 
        self.__thisFileMenu.add_command(label="Open", 
                                        command=self.__openFile) 
          
        # To save current file 
        self.__thisFileMenu.add_command(label="Save", 
                                        command=self.__saveFile)     
  
        # To create a line in the dialog         
        self.__thisFileMenu.add_separator()                                          
        self.__thisFileMenu.add_command(label="Exit", 
                                        command=self.__quit) 
        self.__thisMenuBar.add_cascade(label="File", 
                                       menu=self.__thisFileMenu)      
          
        # To give a feature of cut  
        self.__thisEditMenu.add_command(label="Cut", 
                                        command=self.__cut)              
      
        # to give a feature of copy     
        self.__thisEditMenu.add_command(label="Copy", 
                                        command=self.__copy)          
          
        # To give a feature of paste 
        self.__thisEditMenu.add_command(label="Paste", 
                                        command=self.__paste)          
          
        # To give a feature of editing 
        self.__thisMenuBar.add_cascade(label="Edit", 
                                       menu=self.__thisEditMenu) 
             
          # To create a feature of description of the notepad 
        self.__thisHelpMenu.add_command(label="About Notepad", 
                                        command=self.__showAbout)  
        self.__thisMenuBar.add_cascade(label="Help", 
                                       menu=self.__thisHelpMenu) 
                            
        self.__root.config(menu=self.__thisMenuBar) 
  
        self.__thisScrollBar.pack(side=tk.RIGHT,fill=tk.Y)                     
          
        # Scrollbar will adjust automatically according to the content         
        self.__thisScrollBar.config(command=self.__thisTextArea.yview)      
        self.__thisTextArea.config(yscrollcommand=self.__thisScrollBar.set)
        self.set_state(1)
      
          
    def __quit(self):
        if len(self.get_text()) > 1:
            if not tk.messagebox.askyesno("Warning", "Exit notepad without saving?", icon = "warning"):
                return
        self.__root.destroy() 
        self.set_state(0)

    def __openFile(self): 
          
        self.__file = tk.filedialog.askopenfilename(defaultextension=".txt", 
                                                    filetypes=[("All Files","*.*"), 
                                                    ("Text Documents","*.txt")],
                                                    initialdir=self.__init_dir) 
  
        if self.__file == "": 
              
            # no file to open 
            self.__file = None
        else: 
            # Try to open the file 
            # set the window title 
            self.__root.title(os.path.basename(self.__file) + " - Notepad") 
            self.__thisTextArea.delete(1.0,tk.END) 
  
            file = open(self.__file,"r") 
  
            self.__thisTextArea.insert(1.0,file.read()) 
  
            file.close() 
  
          
    def __newFile(self): 
        self.__root.title("Untitled - Notepad") 
        self.__file = None
        self.__thisTextArea.delete(1.0,tk.END) 
  
    def __saveFile(self): 
  
        if self.__file == None: 
            # Save as new file 
            self.__file = tk.filedialog.asksaveasfilename(initialfile='Untitled.txt',
                                                        initialdir=self.__init_dir,
                                                        defaultextension=".txt", 
                                                        filetypes=[("All Files","*.*"), 
                                                        ("Text Documents","*.txt")]) 
  
            if self.__file == "": 
                self.__file = None
            else: 
                # Try to save the file 
                file = open(self.__file,"w") 
                file.write(self.__thisTextArea.get(1.0,tk.END)) 
                file.close() 
                  
                # Change the window title 
                self.__root.title(os.path.basename(self.__file) + " - Notepad") 
                  
              
        else:
            if not tk.messagebox.askyesno("Warning", "Overwrite file?", icon = "warning"):
                # Save as new file 
                self.__file = tk.filedialog.asksaveasfilename(initialfile='Untitled.txt',
                                                            initialdir=self.__init_dir,
                                                            defaultextension=".txt", 
                                                            filetypes=[("All Files","*.*"), 
                                                            ("Text Documents","*.txt")]) 
                
                if self.__file == "": 
                    self.__file = None
                    return

            file = open(self.__file,"w") 
            file.write(self.__thisTextArea.get(1.0,tk.END)) 
            file.close() 

            # Change the window title 
            self.__root.title(os.path.basename(self.__file) + " - Notepad") 

    def __showAbout(self): 
        tk.messagebox.showinfo("RAGU Notepad","Notepad designed to hold session notes. Radar data file names will be added to new notepad line in a comma-separated value format. Type file notes following file name.") 

    # write_track adds the current track from gui to a new line
    def write_track(self, fn=None):
        print('write',fn)
        if fn:
            text = self.get_text()
            if fn in text:
                self.search_text(fn)
            else:
                if len(text) > 1:
                    fn = "\n" + fn
                self.__thisTextArea.insert(tk.END, fn + ",")
                self.__thisTextArea.see("insert")


    # search_text
    def search_text(self, lookup):
        for num, line in enumerate(self.get_text().splitlines()):
            if lookup in line:
                self.__thisTextArea.mark_set("insert", str(num) + "." + str(len(line)))
                self.__thisTextArea.see("insert")


    # get_text returns the text entry string
    def get_text(self):
        return self.__thisTextArea.get(1.0, tk.END)
  
    def __cut(self): 
        self.__thisTextArea.event_generate("<<Cut>>") 
  
    def __copy(self): 
        self.__thisTextArea.event_generate("<<Copy>>")
  
    def __paste(self): 
        self.__thisTextArea.event_generate("<<Paste>>") 
  
    def get_state(self):
        return self.__state

    def set_state(self, state=0):
        self.__state = state