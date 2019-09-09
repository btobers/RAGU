import h5py
import numpy as np
from tools import *
import matplotlib.pyplot as plt
import sys

class imPick:
    # imPick is a class to pick horizons from a radar image
    def __init__(self):
        sys.exit()

    def picking(self):
        # change status of pick_state based on button click
        if self.f_loadName:
            if self.pick_state == 0:
                self.pick_state = 1
                self.pick_dict["layer_" + str(self.pick_layer)] = np.ones(self.data["num_trace"])*-1
                self.pickButton.configure(fg = "red")
            elif self.pick_state == 1:
                self.pick_state = 0
                self.pick_layer += 1
                # save picked lines to old variable and clear line variables
                self.xln_old.extend(self.xln)
                self.yln_old.extend(self.yln)
                del self.xln[:]
                del self.yln[:]
                # plot saved pick in green
                self.pick.set_data(self.xln, self.yln)
                self.saved_pick.set_data(self.xln_old, self.yln_old)
                self.fig.canvas.draw()
                self.pickButton.configure(fg = "green")

    def addseg(self, event):
        # add line segments with user input
        # find nearest index to event.xdata for plotting on basemap and for linearly interpolating twtt between points
        pick_idx_1 = utils.find_nearest(self.data["dist"], event.xdata)
        # check if picking state is a go
        if self.pick_state == 1:
            if (event.inaxes != self.ax):
                return
            self.xln.append(event.xdata)
            self.yln.append(event.ydata)
            num_pick = len(self.xln)
            if num_pick >= 2:
                # if there are at least two picked points, find range of all trace numbers within their range
                pick_idx_0 = utils.find_nearest(self.data["dist"], self.xln[-2])
                self.pick_dict["layer_" + str(self.pick_layer)][pick_idx_0] = self.yln[-2]
                self.pick_dict["layer_" + str(self.pick_layer)][pick_idx_1] = self.yln[-1]
                self.pick_idx = np.arange(pick_idx_0,pick_idx_1 + 1)
                # linearly interpolate twtt values between pick points at idx_0 and idx_1
                self.pick_dict["layer_" + str(self.pick_layer)][self.pick_idx] = np.interp(self.pick_idx, [pick_idx_0,pick_idx_1], [self.yln[-2],self.yln[-1]])
            
            # Redraw pick quickly with blitting
            self.pick.set_data(self.xln, self.yln)
            self.dataCanvas.restore_region(self.axbg)
            self.ax.draw_artist(self.pick)
            self.dataCanvas.blit(self.ax.bbox)

        if self.map_loadName:
            # basemap open, plot picked location regardless of picking state
            if self.basemap_state == 1:
                # plot pick location on basemap
                if self.pick_loc:
                    self.pick_loc.remove()
                self.pick_loc = self.map_fig_ax.scatter(self.xdat[pick_idx_1],self.ydat[pick_idx_1],c="w",marker="x",zorder=3)
                self.map_fig.canvas.draw()

    def onkey(self, event):
        # on-key commands
        if event.key =="c":
            # clear the drawing of line segments
            self.clear_picks()
        elif event.key =="backspace":
            # remove last segment
            self.clear_last()
        elif event.key =="escape":
            self.close_window()

    def clear_picks(self):
        # clear all picks
        if len(self.xln) and messagebox.askokcancel("Warning", "Clear all picks?", icon = "warning") == True:
            del self.xln[:]
            del self.yln[:]
            self.pick.set_data(self.xln, self.yln)
            self.fig.canvas.draw()

    def clear_last(self):
        # clear last pick
        if len(self.xln) and len(self.yln) > 0:
            del self.xln[-1:]
            del self.yln[-1:]
            self.pick.set_data(self.xln, self.yln)
            self.fig.canvas.draw()

    def show_radar(self):
        # toggle to radar data
        if self.im_clut.get_visible():
            # get clutter colormap slider values for reviewing
            self.clut_cmin = self.s_cmin.val
            self.clut_cmax = self.s_cmax.val
            # set button relief
            self.clutterButton.config(relief="raised")
            self.radarButton.config(relief="sunken")
            # set colorbar initial values to previous values
            self.s_cmin.valinit = self.data_cmin
            self.s_cmax.valinit = self.data_cmax
            # set colorbar bounds
            self.s_cmin.valmin = self.mindB_data - 10
            self.s_cmin.valmax = self.mindB_data + 10
            self.s_cmax.valmin = -10
            self.s_cmax.valmax = 10
            # reverse visilibilty
            self.im_clut.set_visible(False)
            self.im_data.set_visible(True)
            # redraw canvas
            self.fig.canvas.draw()

    def show_clutter(self):
        # toggle to clutter sim viewing
        if self.im_data.get_visible():
            # get radar data colormap slider values for reviewing
            self.data_cmin = self.s_cmin.val
            self.data_cmax = self.s_cmax.val
            # set button relief
            self.radarButton.config(relief="raised")
            self.clutterButton.config(relief="sunken")
            if not self.clut_imSwitch_flag:
                # if this is the first time viewing the clutter sim, set colorbar limits to initial values
                self.s_cmin.valmin = self.mindB_clut - 10
                self.s_cmin.valmax = self.mindB_clut + 10
                self.s_cmin.valinit = self.mindB_clut
                self.s_cmax.valmin = -10
                self.s_cmax.valmax = 10
                self.s_cmax.valinit = 0
            else: 
                # if clutter has been shown before revert to previous colorbar values
                self.im_clut.set_clim([self.clut_cmin, self.clut_cmax])

            # reverse visilibilty
            self.im_data.set_visible(False)
            self.im_clut.set_visible(True)
            # set flag to indicate that clutter has been viewed for resetting colorbar limits
            self.clut_imSwitch_flag is True    
            # redraw canvas
            self.fig.canvas.draw()

    def cmap_update(self, s=None):
        # method to update image colormap based on slider values
        try:
            if self.im_data.get_visible():
                # apply slider values to visible image
                self.data_cmin = self.s_cmin.val
                self.data_cmax = self.s_cmax.val
                self.im_data.set_clim([self.data_cmin, self.data_cmax])
            else:
                self.clut_cmin = self.s_cmin.val
                self.clut_cmax = self.s_cmax.val
                self.im_clut.set_clim([self.clut_cmin, self.clut_cmax])
            self.fig.canvas.draw()
        except Exception as err:
            print("cmap_update error: " + str(err))

    def cmap_reset(self, event):
        # reset sliders to initial values
        if self.im_data.get_visible():
            print('data')
            self.s_cmin.reset()
            self.s_cmax.reset()
        else:
            print('clut')
            # if clutter is displayed, change slider bounds
            self.s_cmin.valmin = self.mindB_clut - 10
            self.s_cmin.valmax = self.mindB_clut + 10
            self.s_cmin.valinit = self.mindB_clut
            # slider max bounds will be same as for real data
            self.s_cmax.reset()

    def close_window(self):
        # destroy canvas
        # first check if picks have been made and saved
        if len(self.xln) > 0 and self.f_saveName == "":
            if messagebox.askokcancel("Warning", "Exit NOSEpick without saving picks?", icon = "warning") == True:
                self.master.destroy()
        else:
            self.master.destroy()

    def save_warning(self):
        # warning to save picks before loading next file
        # first check if picks have been made and saved
        if len(self.xln) > 0 and self.f_saveName == "":
            if messagebox.askokcancel("Warning", "Load next track without saving picks?", icon = "warning") == True:
                # clear picks
                self.clear_picks()
                return True
        else: 
            return True

    def basemap_close(self):
        # close the basemap window and set state
        self.basemap_window.destroy()
        self.basemap_state = 0




