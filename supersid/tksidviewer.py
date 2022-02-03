"""
tkSidViewer class - a graphical user interface for SID based on tkinter.

# created on 20150421
# first official release 20150801

2017/09/01: add vertical lines on the plot for each monitored station

"""
import sys
import subprocess

import tkinter as tk
import tkinter.messagebox as MessageBox
import tkinter.filedialog as FileDialog

import math
import numpy as np
import matplotlib
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg as FigureCanvas
from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk
from matplotlib.figure import Figure

from supersid_common import script_relative_to_cwd_relative


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
        matplotlib.use('TkAgg')
        self.version = "1.4 20170920 (tk)"
        self.controller = controller  # previously referred as 'parent'
        self.tk_root = tk.Tk()
        self.tk_root.title("supersid @ " + self.controller.config['site_name'])
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
        try:
            # full screen, works in Windows but not in Linux
            self.tk_root.state('zoomed')
        except Exception:
            try:
                # large window but doesn't match the screen in Windows
                w = self.tk_root.winfo_screenwidth()
                h = self.tk_root.winfo_screenheight()
                self.tk_root.geometry("%dx%d+0+0" % (w, h))
            except Exception:
                try:
                    # full screen, but not resizeable
                    self.tk_root.attributes("-fullscreen", True)
                except Exception:
                    pass

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
        self.canvas._tkcanvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.axes = self.psd_figure.add_subplot(111)
        self.axes.format_coord = Formatter()

        # add the psd labels manually for proper layout at startup
        self.axes.set_ylabel("Power Spectral Density (dB/Hz)")
        self.axes.set_xlabel("Frequency")
        self.set_graph_limits()

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
        self.need_refresh = False

    def run(self):
        self.need_refresh = False
        self.refresh_psd()  # start the re-draw loop
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
        """Update the main frame by changing the message in status bar."""
        if self.running:
            self.statusbar_txt.set(message)

    def set_graph_limits(self):
        # use the entire x-axis for data
        self.axes.set_xlim([
            0, self.controller.config['audio_sampling_rate'] // 2])

        psd_min = self.controller.config['psd_min']
        psd_max = self.controller.config['psd_max']
        psd_ticks = self.controller.config['psd_ticks']
        if not math.isnan(psd_min):
            # set minimum for the y-axis if not configured as NaN
            self.axes.set_ylim(bottom=psd_min)
        if not math.isnan(psd_max):
            # set maximum for the y-axis if not configured as NaN
            self.axes.set_ylim(top=psd_max)
        if (psd_ticks
                and (not math.isnan(psd_min))
                and (not math.isnan(psd_max))):
            self.axes.set_yticks(np.linspace(psd_min, psd_max, psd_ticks))

    def get_psd(self, data, NFFT, FS):
        """Call 'psd' within axes, both calculates and plots the spectrum."""
        try:
            self.axes.clear()
            Pxx = {}
            for channel in range(self.controller.config['Channels']):
                Pxx[channel], freqs = self.axes.psd(
                    data[:, channel], NFFT=NFFT, Fs=FS)
            self.set_graph_limits()
            self.need_refresh = True
        except RuntimeError as err_re:
            print("Warning:", err_re)
            Pxx, freqs = None, None
        else:
            bottom, top = self.axes.get_ylim()
            dist = top - bottom
            for s in self.controller.config.stations:
                freq = int(s['frequency'])
                self.axes.axvline(x=freq, color='r')
                self.axes.text(freq, bottom + (dist * 0.95), s['call_sign'],
                               horizontalalignment='center',
                               bbox={'facecolor': 'w', 'alpha': 0.5,
                                     'fill': True})
        return Pxx, freqs

    def refresh_psd(self, z=None):
        """Redraw the graphic PSD plot if needed.

        i.e.new data have been given to get_psd
        """
        if self.need_refresh:
            try:
                self.canvas.draw()
                self.need_refresh = False
            except IndexError as err_idx:
                print("Warning:", err_idx)
        self.tk_root.after(2000, self.refresh_psd)

    def save_file(self, param=None):
        """Save the files as per user's menu choice."""
        param = param if isinstance(
            param, str) else param.keysym  # which is the letter with the CTRL-
        if param == 'r':
            saved_files = self.controller.save_current_buffers(
                log_type='raw',
                log_format='both')
        elif param == 'f':
            saved_files = self.controller.save_current_buffers(
                log_type='filtered',
                log_format='both')
        elif param == 'e':
            saved_files = self.controller.save_current_buffers(
                log_type='raw',
                log_format='both_extended')
        elif param == 's':
            filename = self.AskSaveasFilename()
            if filename:
                saved_files = self.controller.save_current_buffers(
                    filename,
                    log_type='filtered',
                    log_format='supersid')
            else:
                saved_files = None
        if saved_files:
            MessageBox.showinfo("SuperSID files saved", "\n".join(saved_files))

    def on_plot(self, dummy=None):
        """Save current buffers (raw) and display the data using supersid_plot.
        Using a separate process to prevent interference with data capture
        """
        filenames = self.controller.save_current_buffers(
            log_format='supersid_format')
        assert (1 == len(filenames)), \
            f"expected exactly one saved file, got {len(filenames)}"
        assert (1 == len(self.controller.config.filenames)), \
            "expected exactly one configuration file, got " \
            f"{len(self.controller.config.filenames)}"
        print("plotting", filenames[0])
        subprocess.Popen([
            sys.executable,
            script_relative_to_cwd_relative('supersid_plot.py'),
            '-f',
            filenames[0],
            '-c',
            script_relative_to_cwd_relative(
                self.controller.config.filenames[0])])

    def on_about(self):
        """Display the About box message."""
        MessageBox.showinfo("SuperSID", self.controller.about_app())

    def AskSaveasFilename(
            self,
            title='Save File',
            filetypes=None,
            initialfile=''):
        """Return a string containing file name.

        the calling routine will need to open the file
        """
        if filetypes is None:
            filetypes = [
                ('CSV File', '*.csv'),
                ('Any File', '*.*')]
        fileName = FileDialog.asksaveasfilename(parent=self.tk_root,
                                                filetypes=filetypes,
                                                initialfile=initialfile,
                                                title=title)
        return fileName
