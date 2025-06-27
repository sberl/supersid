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
from datetime import datetime, timezone, timedelta
import numpy as np
import matplotlib.ticker
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg as FigureCanvas
from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk
from matplotlib.figure import Figure

from supersid_common import script_relative_to_cwd_relative, is_script


def psd_format_coord(x, y):
    """Display cursor position in lower right of display"""
    bin_freq, bin_power = x, y
    return f"frequency={bin_freq:.0f} power={bin_power:.3f}"


def safe_log10(data):
    """safe log for data type <class 'numpy.ndarray'>"""
    result = np.log10(data, where=data>0)
    result[data<=0] = 0
    return result


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
        self.waterfall = [None] * controller.config['Channels']
        self.xlim = (0, self.controller.config['audio_sampling_rate'] // 2)

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
#        disabled as there is no maximized version for Windows
#        that shows the matplotlib buttons when maximized
#        try:
#            # full screen, works in Windows but not in Linux
#            self.tk_root.state('zoomed')
#        except Exception:
#            try:
#                # large window but doesn't match the screen in Windows
#                w = self.tk_root.winfo_screenwidth()
#                h = self.tk_root.winfo_screenheight()
#                self.tk_root.geometry("%dx%d+0+0" % (w, h))
#            except Exception:
#                try:
#                    # full screen, but not resizeable
#                    self.tk_root.attributes("-fullscreen", True)
#                except Exception:
#                    pass

        self.tk_root.bind("<Configure>", self.onsize)

        # FigureCanvas
        self.figure = Figure(facecolor='beige')
        self.canvas = FigureCanvas(self.figure, master=self.tk_root)
        self.canvas.draw()
        self.canvas \
            .get_tk_widget() \
            .pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.toolbar = NavigationToolbar2Tk(self.canvas, self.tk_root)
        self.toolbar.update()

        if self.controller.config['waterfall_samples']:
            num_subplots = 1 + self.controller.config['Channels']
        else:
            num_subplots = 1
        self.axarr = self.figure.subplots(
            num_subplots,
            1,
            sharex=True,
            gridspec_kw={'wspace': 0, 'hspace': 0})

        self.psd_axes = self.figure.axes[0]
        self.waterfall_axes = self.figure.axes[1:]

        # set formatter for position under the mouse pointer
        self.psd_axes.format_coord = psd_format_coord
        for ax in self.waterfall_axes:
            ax.format_coord = self.waterfall_format_coord
            self.waterfall_set_yticks(ax)

        self.psd_axes.grid(True)

        self.station_labels = []
        self.line = {}              # no psd data yet
        self.mesh = {}              # no waterfall data yet
        self.y_max = -float("inf")  # negative infinite y max
        self.y_min = +float("inf")  # positive infinite y min

        # add the psd labels manually for proper layout at startup
        self.psd_axes.set_ylabel("Power Spectral Density (dB/Hz)")
        for i in range(len(self.figure.axes) - 1):
            self.figure.axes[i].set_xlabel(None)
        self.figure.axes[-1].set_xlabel("Frequency")

        self.set_x_limits()

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
        self.need_psd_refresh = False
        self.pxx = []
        self.freqs = []
        self.need_text_refresh = False
        self.message = ""

    def waterfall_set_yticks(self, ax):
        """set the y ticks of the waterfall diagram at fixed positions"""
        waterfall_samples = self.controller.config['waterfall_samples']
        log_interval = self.controller.config['log_interval']
        samples_per_minute = 60 / log_interval

        positions = []
        labels = []
        row = waterfall_samples - samples_per_minute
        minutes = -1
        while row >= 0:
            positions.append(int(row))
            if 0 == (minutes % 3):
                labels.append(f"{minutes}:00")
            else:
                labels.append("")
            row -= samples_per_minute
            minutes -= 1
        ax.yaxis.set_major_locator(matplotlib.ticker.FixedLocator(positions))
        ax.yaxis.set_major_formatter(matplotlib.ticker.FixedFormatter(labels))

    def waterfall_format_coord(self, x, y):
        """Display cursor position in lower right of display"""
        bin_freq = x

        waterfall_samples = self.controller.config['waterfall_samples']
        log_interval = self.controller.config['log_interval']

        # round down the current time based on log_interval
        utcnow = datetime.now(timezone.utc)
        utcnow = utcnow.replace(second = (utcnow.second // log_interval) * log_interval)

        # add the offset based on the y coordinate
        seconds_relative = (int(y) - waterfall_samples) * log_interval
        y_time = utcnow + timedelta(seconds=seconds_relative)

        return f"frequency={bin_freq:.0f} UTC={y_time.strftime('%H:%M:%S')}"

    def run(self):
        """actions on start"""
        self.running = True
        self.refresh_psd()  # start the re-draw loop
        self.tk_root.mainloop()
        self.running = False

    def close(self, force_close=True):
        """actions on close"""
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
        _ = event
        width = self.tk_root.winfo_width()
        height = self.tk_root.winfo_height()

        left_gap = 70       # px
        bottom_gap = 50     # px
        right_gap = 10      # px
        top_gap = 10        # px

        left = left_gap / width
        bottom = bottom_gap / height
        right = (width - right_gap) / width
        top = (height - top_gap) / height
        self.figure.subplots_adjust(
            left=left,
            bottom=bottom,
            right=right,
            top=top)

    def status_display(self, message):
        """Update the main frame by changing the message in status bar."""
        self.message = message
        self.need_text_refresh = True

    def set_x_limits(self):
        """set the psd x limits on change of the diagram"""
        fs = self.controller.config['audio_sampling_rate']
        # nfft = 1024 for 44100 and 48000,
        #        2048 for 96000,
        #        4096 for 192000
        # -> the frequency resolution is constant
        nfft = max(1024, 1024 * fs // 48000)
        if fs > 96000:
            step = 10000    # one tick per 10 kHz
        elif fs > 48000:
            step = 5000     # one tick per 5 kHz
        else:
            step = 2500     # one tick per 2.5 kHz
        x_steps = (fs // 2) // step
        x_max = x_steps * step

        # use the entire x-axis for data
        self.t = np.arange(0, (fs/2)+1, fs/nfft)    # x-axis data (frequency)
        self.psd_axes.set_xticks(np.linspace(0, x_max, x_steps+1))
        self.psd_axes.set_xlim(self.xlim)

    def set_y_limits(self):
        """set the psd y limits on change of the diagram"""
        psd_min = self.controller.config['psd_min']
        psd_max = self.controller.config['psd_max']
        psd_ticks = self.controller.config['psd_ticks']
        if (psd_ticks
                and (not math.isnan(psd_min))
                and (not math.isnan(psd_max))):
            self.psd_axes.set_yticks(np.linspace(psd_min, psd_max, psd_ticks))
        elif (not np.isinf(self.y_min) and (not np.isinf(self.y_max))):
            l = matplotlib.ticker.AutoLocator()
            l.create_dummy_axis()
            ticks = l.tick_values(self.y_min, self.y_max)

            # correct min/max if the outer ticks are already outside
            if ticks[0] < self.y_min:
                self.y_min = ticks[0]
            if ticks[-1] > self.y_max:
                self.y_max = ticks[-1]

            self.psd_axes.set_yticks(ticks)
        if not math.isnan(psd_min):
            # set minimum for the y-axis if not configured as NaN
            self.psd_axes.set_ylim(bottom=psd_min)
        if not math.isnan(psd_max):
            # set maximum for the y-axis if not configured as NaN
            self.psd_axes.set_ylim(top=psd_max)

    def update_psd(self, pxx, freqs):
        """
        decouple the PSD calculation (done in timer context)
        from displaying the data with TK/matplotlib
        """
        self.pxx = pxx
        self.freqs = freqs
        self.need_psd_refresh = True

    def redraw_psd(self):
        """Redraw the graphic PSD plot"""
        y_axis_changed = False
        psd_max = self.controller.config['psd_max']
        psd_min = self.controller.config['psd_min']
        for channel in range(self.controller.config['Channels']):
            y = 10 * safe_log10(self.pxx[channel])

            if channel not in self.line:
                self.line[channel], = self.psd_axes.plot(self.t, y)
            else:
                self.line[channel].set_data(self.t, y)

            # change y labels if new min/max is reached
            # if not otherwise configured
            if math.isnan(psd_max):
                if np.max(y) > self.y_max:
                    self.y_max = np.max(y)
                    y_axis_changed = True
            if math.isnan(psd_min):
                if np.min(y) < self.y_min:
                    self.y_min = np.min(y)
                    y_axis_changed = True

            if self.controller.config['waterfall_samples']:
                pxx = safe_log10(self.pxx[channel][:-1].reshape(
                    (1, self.pxx[channel].shape[0] - 1)))
                if self.waterfall[channel] is None:
                    min_val = pxx.min()
                    self.waterfall[channel] = np.full(
                        (
                            self.controller.config['waterfall_samples'],
                            self.pxx[channel].shape[0] - 1
                        ),
                        min_val)
                self.waterfall[channel] = np.append(
                    self.waterfall[channel], pxx, axis=0)
                if (self.waterfall[channel].shape[0] >
                        self.controller.config['waterfall_samples']):
                    self.waterfall[channel] = self.waterfall[channel][1:]
                if channel not in self.mesh:
                    self.mesh[channel] = self.waterfall_axes[channel].pcolormesh(
                        self.freqs,
                        range(self.waterfall[channel].shape[0]+1), self.waterfall[channel])
                else:
                    self.mesh[channel].set_array(self.waterfall[channel])

        if not math.isnan(psd_max):
            # psd_max is configured ...
            if np.isinf(self.y_max):
                # ... but y_max not yet set
                # set it now
                self.y_max = psd_max
                y_axis_changed = True

        if not math.isnan(psd_min):
            # psd_min is configured ...
            if np.isinf(self.y_min):
                # ... but y_min not yet set
                # set it now
                self.y_min = psd_min
                y_axis_changed = True

        if y_axis_changed:
            self.set_y_limits()
            self.mark_stations()

        # required to update canvas and attached toolbar!
        self.canvas.draw()

    def mark_stations(self):
        """Place the horizontal markers for the observed stations."""
        for label in self.station_labels:
            label.remove()
        self.station_labels = []
        prop_cycle = plt.rcParams['axes.prop_cycle']
        colors = prop_cycle.by_key()['color']
        bottom, top = self.psd_axes.get_ylim()
        dist = top - bottom
        top = True
        for s in self.controller.config.stations:
            color = colors[s['channel']]
            freq = int(s['frequency'])
            self.psd_axes.axvline(x=freq, color=color, alpha=0.5)
            if top:
                label = self.psd_axes.text(freq, bottom + (dist * 0.975),
                                           s['call_sign'],
                                           verticalalignment='top',
                                           horizontalalignment='center',
                                           rotation=90,
                                           bbox={'facecolor': color,
                                                 'alpha': 0.5,
                                                 'fill': True})
            else:
                label = self.psd_axes.text(freq, bottom + (dist * 0.025),
                                           s['call_sign'],
                                           verticalalignment='baseline',
                                           horizontalalignment='center',
                                           rotation=90,
                                           bbox={'facecolor': color,
                                                 'alpha': 0.5,
                                                 'fill': True})
            top = not top
            self.station_labels.append(label)

    def refresh_psd(self):
        """Redraw the graphic PSD plot if needed.
        """
        if self.running:
            if self.need_psd_refresh:
                self.redraw_psd()
                self.need_psd_refresh = False

            if self.need_text_refresh:
                self.statusbar_txt.set(self.message)
                self.need_text_refresh = False

            self.tk_root.after(100, self.refresh_psd)

    def save_file(self, param=None):
        """Save the files as per user's menu choice."""
        saved_files = None
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
            filename = self.asksaveasfilename()
            if filename:
                saved_files = self.controller.save_current_buffers(
                    filename,
                    log_type='filtered',
                    log_format='supersid')
        if saved_files:
            MessageBox.showinfo("SuperSID files saved", "\n".join(saved_files))

    def on_plot(self, _=None):
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
        if is_script():
            cmd = [sys.executable,
                   script_relative_to_cwd_relative('supersid_plot.py')]
        else:
            cmd = [script_relative_to_cwd_relative('supersid_plot.exe')]
        with subprocess.Popen(cmd + [
            '-f',
            filenames[0],
            '-c',
            self.controller.config.filenames[0]]) as _:
            pass

    def on_about(self):
        """Display the About box message."""
        MessageBox.showinfo("SuperSID", self.controller.about_app())

    def asksaveasfilename(
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
        file_name = FileDialog.asksaveasfilename(parent=self.tk_root,
                                                 filetypes=filetypes,
                                                 initialfile=initialfile,
                                                 title=title)
        return file_name
