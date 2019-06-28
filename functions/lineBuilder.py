from matplotlib import pyplot as plt

class LineBuilder:
    def __init__(self, line):
        self.line = line
        self.xs = list(line.get_xdata())
        self.ys = list(line.get_ydata())
        self.cid = line.figure.canvas.mpl_connect('button_press_event', self)
        self.cid2 = line.figure.canvas.mpl_connect('key_press_event', self.clear_canvas)
        self.cid3 = line.figure.canvas.mpl_connect('key_press_event', self.remove_last)

    def __call__(self, event):
        if event.inaxes!=self.line.axes: return
        self.xs.append(event.xdata)
        self.ys.append(event.ydata)
        self.line.set_data(self.xs, self.ys)
        self.line.figure.canvas.draw()

    def clear_canvas(self, event):
        if event.key =='c':
            if len(self.xs) and len(self.ys) > 0:
                del self.xs[:]
                del self.ys[:]
                self.line.set_data(self.xs, self.ys)
                self.line.figure.canvas.draw()

    def remove_last(self, event):
        if event.key =='backspace':
            if len(self.xs) and len(self.ys) > 0:
                del self.xs[-1:]
                del self.ys[-1:]
                self.line.set_data(self.xs, self.ys)
                self.line.figure.canvas.draw()
                
fig = plt.figure()
ax = fig.add_subplot(111)
ax.set_title('click to build line segments')
line, = ax.plot([],[],'r')  # empty line
linebuilder = LineBuilder(line)
plt.show()


