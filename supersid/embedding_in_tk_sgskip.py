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

import tkinter as tk
import numpy as np
import random

# Implement the default Matplotlib key bindings.
from matplotlib.backend_bases import key_press_handler
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg,
                                               NavigationToolbar2Tk)
from matplotlib.figure import Figure


class Formatter(object):
    def __init__(self):
        pass

    def __call__(self, bin_freq, bin_power):
        """Display cursor position in lower right of display"""
        return "frequency=%.0f  " % bin_freq + " power=%.3f  " % bin_power


class tkSidViewer():
    """Create the Tkinter GUI."""

    def __init__(self):
        self.tk_root = tk.Tk()
        self.tk_root.wm_title("Embedding in Tk")

        fig = Figure(figsize=(5, 4), dpi=100)
        self.t = np.arange(0, 3, .01)
        self.axes = fig.add_subplot()
        self.axes.format_coord = Formatter()
        self.line, = self.axes.plot(self.t, 2 * np.sin(2 * np.pi * self.t))
        self.axes.set_xlabel("time [s]")
        self.axes.set_ylabel("f(t)")

        self.canvas = FigureCanvasTkAgg(fig, master=self.tk_root)  # A tk.DrawingArea.
        self.canvas.draw()

        # pack_toolbar=False will make it easier to use a layout manager later on.
        toolbar = NavigationToolbar2Tk(self.canvas, self.tk_root, pack_toolbar=False)
        toolbar.update()

        self.canvas.mpl_connect(
            "key_press_event", lambda event: print(f"you pressed {event.key}"))
        self.canvas.mpl_connect("key_press_event", key_press_handler)

        button_quit = tk.Button(master=self.tk_root, text="Quit", command=self.tk_root.destroy)

        slider_update = tk.Scale(self.tk_root, from_=1, to=5, orient=tk.HORIZONTAL,
                                      command=self.update_frequency, label="Frequency [Hz]")

        # Packing order is important. Widgets are processed sequentially and if there
        # is no space left, because the window is too small, they are not displayed.
        # The canvas is rather flexible in its size, so we pack it last which makes
        # sure the UI controls are displayed as long as possible.
        button_quit.pack(side=tk.BOTTOM)
        slider_update.pack(side=tk.BOTTOM)
        toolbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    def update_frequency(self, new_val):
        # retrieve frequency
        f = float(new_val)

        # update data
        y = 2 * np.sin(2 * np.pi * f * self.t)
        self.line.set_data(self.t, y)

        # required to update canvas and attached toolbar!
        self.canvas.draw()

        if gc.garbage:
            print("gc.garbage")     # did not yet trigger
            print(gc.garbage)       # did not yet trigger

        objgraph.show_growth()      # triggers rarely when klicking the cntrol for
                                    # the frequency and moving the mouse wildly

    def run(self):
        self.refresh_psd()  # start the re-draw loop
        self.tk_root.mainloop()

    def refresh_psd(self, z=None):
        self.update_frequency(random.randint(1, 10))
        self.tk_root.after(random.randint(10, 50), self.refresh_psd)


def main():
    viewer = tkSidViewer()
    viewer.run()


if __name__ == "__main__":
    main()
