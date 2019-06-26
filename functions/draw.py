try:
    import Tkinter as tk
    
except:
    import tkinter as tk

line = []

def on_click(event):
    global line
    if len(line) == 0:
        # define line starting point
        line=[event.x, event.y]

    elif len(line) >=  2:
        # starting point has been defined
        line.extend([event.x, event.y])
        canvas.create_line(*line,fill="red",width=2)
    
def clear_canvas(event):
    global line
    canvas.delete('all')
    line = []

def remove_last(event):
    global line
    if len(line) > 0:
        del line[-2:]
        canvas.delete('all')
        if len(line) >= 4:
            canvas.create_line(*line,fill="red",width=2)

def close_window ():
    root.destroy()


root = tk.Tk()
canvas = tk.Canvas(root, bg='white', width=800, height=800)
canvas.pack()

button = tk.Button(text = "Click and Quit", command = close_window)
button.pack()

canvas.bind("<Button-1>", on_click) 
root.bind("<Key-c>", clear_canvas)
root.bind("<BackSpace>", remove_last)

root.mainloop()

draw_coords = line

print(draw_coords)