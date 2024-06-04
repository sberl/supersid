"""
===============
Embedding in Tk
===============

"""

# memory leak investigation
# 
# measure
#   mprof run python embedding_in_tk_sgskip.py
#   mprof plot

import gc
import objgraph
import random
import argparse
from supersid_common import exist_file
from config import readConfig, CONFIG_FILE_NAME

import tkinter as tk
import tkinter.messagebox as MessageBox
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg as FigureCanvas
from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk
from matplotlib.figure import Figure
from matplotlib.mlab import psd as mlab_psd


class Formatter(object):
    def __init__(self):
        pass

    def __call__(self, bin_freq, bin_power):
        """Display cursor position in lower right of display"""
        return "frequency=%.0f  " % bin_freq + " power=%.3f  " % bin_power


class tkSidViewer():
    """Create the Tkinter GUI."""

    def __init__(self, controller):
        """Init SuperSID Viewer using Tkinter GUI for standalone and client.

        Creation of the Frame with menu and graph display using matplotlib
        """
        self.version = "1.4 20170920 (tk)"
        self.controller = controller  # previously referred as 'parent'
        self.tk_root = tk.Tk()
        self.tk_root.wm_title("supersid @ " + self.controller.config['site_name'])
        self.running = False

        # All Menus creation
        menubar = tk.Menu(self.tk_root)
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Save Raw buffers",
                             command=lambda: self.save_file('r'),
                             underline=5, accelerator="Ctrl+R")
        filemenu.add_command(label="Save Filtered buffers",
                             command=lambda: self.save_file('f'),
                             underline=5, accelerator="Ctrl+F")
        filemenu.add_command(label="Save Extended raw buffers",
                             command=lambda: self.save_file('e'),
                             underline=5, accelerator="Ctrl+E")
        filemenu.add_command(label="Save filtered as ...",
                             command=lambda: self.save_file('s'),
                             underline=5, accelerator="Ctrl+S")
        filemenu.add_separator()
        filemenu.add_command(label="Exit",
                             command=lambda: self.close(force_close=False))
        self.tk_root.bind_all("<Control-r>", self.save_file)
        self.tk_root.bind_all("<Control-f>", self.save_file)
        self.tk_root.bind_all("<Control-e>", self.save_file)
        self.tk_root.bind_all("<Control-s>", self.save_file)
        self.tk_root.bind_all("<Control-p>", self.on_plot)
        # user click on the [X] to close the window
        self.tk_root.protocol("WM_DELETE_WINDOW", lambda: self.close(False))
        menubar.add_cascade(label="File", menu=filemenu)

        plotmenu = tk.Menu(menubar, tearoff=0)
        plotmenu.add_command(label="Plot", command=self.on_plot,
                             underline=0, accelerator="Ctrl+P")
        menubar.add_cascade(label="Plot", menu=plotmenu)

        helpmenu = tk.Menu(menubar, tearoff=0)
        helpmenu.add_command(label="About...", command=self.on_about)
        menubar.add_cascade(label="Help", menu=helpmenu)

        self.tk_root.config(menu=menubar)

        self.tk_root.bind("<Configure>", self.onsize)

        # FigureCanvas
        self.psd_figure = Figure(facecolor='beige')
        self.canvas = FigureCanvas(self.psd_figure, master=self.tk_root)
        self.canvas.draw()
        self.canvas \
            .get_tk_widget() \
            .pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.toolbar = NavigationToolbar2Tk(self.canvas, self.tk_root)
        self.toolbar.update()

        FS = self.controller.config['audio_sampling_rate']
        # NFFT = 1024 for 44100 and 48000,
        #        2048 for 96000,
        #        4096 for 192000
        # -> the frequency resolution is constant
        NFFT = max(1024, 1024 * FS // 48000)
        x_steps = ((FS//2) + 4999) // 5000
        x_max = x_steps * 5000
        print(FS, x_steps, x_max)

        self.axes = self.psd_figure.add_subplot()
        self.axes.format_coord = Formatter()
        self.axes.grid(True)

        # add the psd labels manually for proper layout at startup
        self.axes.set_ylabel("Power Spectral Density (dB/Hz)")
        self.axes.set_xlabel("Frequency")
        self.axes.set_xticks(np.linspace(0, x_max, x_steps+1))

        # StatusBar
        self.statusbar_txt = tk.StringVar()

        # width=1 avoids resizing when the length of statusbar_txt changes
        self.label = tk.Label(self.tk_root, bd=1, relief=tk.SUNKEN,
                              anchor=tk.W,
                              textvariable=self.statusbar_txt,
                              font=('arial', 12, 'normal'),
                              width=1)

        self.statusbar_txt.set('Initialization...')
        self.label.pack(fill=tk.X)

        self.t = np.arange(0, (FS/2)+1, FS/NFFT)    # x-axis data (frequency)
        self.line = None                            # no y-data yet
        self.y_max = -float("inf")                  # negative infinite y max
        self.y_min = +float("inf")                  # positive infinite y min

    def run(self):
        self.tk_root.after(1000, self.tick)
        self.running = True
        self.tk_root.mainloop()
        self.running = False

    def close(self, force_close=True):
        if not force_close and MessageBox.askyesno(
                "Confirm exit",
                "Are you sure you want to exit SuperSID?"):
            self.running = False
            self.tk_root.destroy()

    def onsize(self, event):
        """
        Resize the figure to fill the available space.
        The border is defined by left_gap, bottom_gap, right_gap, top_gap.
        """
        width = self.tk_root.winfo_width()
        height = self.tk_root.winfo_height()

        left_gap = 20       # px
        bottom_gap = 20     # px
        right_gap = 10      # px
        top_gap = 10        # px

        left = left_gap / width
        bottom = bottom_gap / height
        right = (width - right_gap) / width
        top = (height - top_gap) / height
        self.psd_figure.subplots_adjust(
            left=left,
            bottom=bottom,
            right=right,
            top=top)
        self.psd_figure.tight_layout()

    def status_display(self, message, level=0, field=0):
        pass

    def get_psd(self, data, NFFT, FS):
        """Call mlab_psd() to calculates the spectrum, then refresh_psd() to plot"""
        try:
            Pxx = {}
            for channel in range(self.controller.config['Channels']):
                Pxx[channel], freqs = \
                    mlab_psd(data[:, channel], NFFT=NFFT, Fs=FS)
            self.refresh_psd(Pxx)
        except RuntimeError as err_re:
            print("Warning:", err_re)
            Pxx, freqs = None, None

        return Pxx, freqs

    def refresh_psd(self, Pxx):
        """Redraw the graphic PSD plot"""
        y = 10 * np.log10(Pxx[0]) # y-axis data (channel 0)

        if self.line is None:
            self.line, = self.axes.plot(self.t, y)
        else:
            self.line.set_data(self.t, y)

        # change y labels if new min/max is reached
        changed = False
        if np.max(y) > self.y_max:
            self.y_max = np.max(y)
            changed = True
        if np.min(y) < self.y_min:
            self.y_min = np.min(y)
            changed = True
        if changed:
            self.axes.set_yticks(np.linspace(self.y_min, self.y_max, 9))

        self.tk_root.after(10, self.draw)
        
    def draw(self):
        # required to update canvas and attached toolbar!
        try:
            self.canvas.draw()
        except IndexError as err_idx:
            print("Warning:", err_idx)

    def save_file(self, param=None):
        pass

    def on_plot(self, dummy=None):
        pass

    def on_about(self):
        """Display the About box message."""
        MessageBox.showinfo("SuperSID", "TODO: self.controller.about_app()")

    def tick(self):
        FS = self.controller.config['audio_sampling_rate']
        # NFFT = 1024 for 44100 and 48000,
        #        2048 for 96000,
        #        4096 for 192000
        # -> the frequency resolution is constant
        NFFT = max(1024, 1024 * FS // 48000)
        data = np.random.rand(FS, self.controller.config['Channels'])
        self.get_psd(data, NFFT, FS)

        if gc.garbage:
            print("gc.garbage")     # did not yet trigger
            print(gc.garbage)       # did not yet trigger

        objgraph.show_growth()      # triggers rarely when klicking the cntrol for
                                    # the frequency and moving the mouse wildly
        self.tk_root.after(1000, self.tick)


class SuperSID():
    running = False  # class attribute indicates the SID application running

    def __init__(self, config_file):
        self.config = readConfig(config_file)
        print(self.config)
        viewer = tkSidViewer(self)
        viewer.run()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-c", "--config", dest="cfg_filename",
        type=exist_file,
        default=CONFIG_FILE_NAME,
        help="Supersid configuration file")
    args = parser.parse_args()

    sid = SuperSID(args.cfg_filename)


if __name__ == "__main__":
    main()
