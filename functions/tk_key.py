import tkinter as tk

class MyApp(object):
    def __init__(self, master):
        self.text = tk.Text(master)
        self.text.bind('<Key>', self.callback)
        self.text.pack()
        self.text.focus()

    def callback(self, event):
        print('{k!r}'.format(k = event.char))

root = tk.Tk()
app = MyApp(root)
root.mainloop()
