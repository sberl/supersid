#!/usr/bin/env python3
"""A GUI for displaying plot of SuperSID data.

    supersid_plot_gui.py
    version: 1.0 for Python 3.5
    Copyright: Eric Gibert
    Created in Sep-2017


    Dependencies:
    - matplotlib
    - pyephem     [ dnf install python3-pyephem ]

"""
import os.path
import argparse
import tkinter as tk
from tkinter import ttk
import matplotlib
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg as FigureCanvas
from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter as ff
import ephem

from sidfile import SidFile
from noaa_flares import NOAA_flares
from supersid_common import exist_file
from config import read_config, print_config, CONFIG_FILE_NAME


def m2hm(x, _):
    """Small function to format the time on horizontal axis - minor ticks."""
    t = matplotlib.dates.num2date(x)
    h = t.hour
    m = t.minute
    # only for odd hours
    return '%(h)02d:%(m)02d' % {'h': h, 'm': m} if h % 2 == 1 else ''


def m2yyyymmdd(x, _):
    """Small function to format the date on horizontal axis - major ticks."""
    t = matplotlib.dates.num2date(x)
    y = t.year
    m = t.month
    d = t.day
    return '%(y)04d-%(m)02d-%(d)02d    .' % {'y': y, 'm': m, 'd': d}


def convert_to_tkinter_color(matplotlib_color):
    r, g, b = matplotlib.colors.to_rgb(matplotlib_color.rstrip('-'))
    r = int(r * 255)
    g = int(g * 255)
    b = int(b * 255)
    tkinter_color = f"#{r:02X}{g:02X}{b:02X}"
    return tkinter_color


class PlotGui(ttk.Frame):
    """Supersid Plot GUI in tk."""

    def __init__(self, parent, cfg, file_list, *args, **kwargs):
        ttk.Frame.__init__(self, parent, *args, **kwargs)
        matplotlib.use('TkAgg')
        self.version = "1.0 20170902 (tk)"
        self.tk_root = parent
        self.cfg = cfg
        self.hidden_stations = set()  # hide the graph if the station in set
        self.color_station = {}       # the color assigned to a station
        self.sid_files = []           # ordered list of sid files read
        self.graph = None
        self.init_gui(file_list)

    def get_station_color(self, call_sign):
        if self.cfg:
            for station in self.cfg.stations:
                if call_sign == station['call_sign']:
                    return station['color'] or None
        return None

    def init_gui(self, file_list):
        """Build GUI."""
        self.tk_root.title('SuperSID Plot')
        color_list = "brgcmy"  # one color per station
        color_idx = 0

        # date of NOAA's data already retrieved, prevent multiple fetch
        self.daysList = {}

        # list of file names (w/o path and extension) as figure's title
        fig_title = []

        self.max_data = -1.0
        # prepare the GUI framework
        self.fig = Figure(facecolor='beige')
        self.canvas = FigureCanvas(self.fig, master=self.tk_root)
        self.canvas.get_tk_widget().pack(side=tk.TOP,
                                         fill=tk.BOTH, expand=True)
        self.graph = self.fig.add_subplot(111)

        self.toolbar = NavigationToolbar2Tk(self.canvas, self.tk_root)
        self.toolbar.update()
        self.canvas._tkcanvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Add data to the graph for each file
        for filename in sorted(file_list):
            sid_file = SidFile(filename)

            # list will be populated if the user click on 'NOAA' button
            sid_file.XRAlist = []

            self.sid_files.append(sid_file)
            self.daysList[sid_file.startTime] = []
            fig_title.append(os.path.basename(filename)[:-4])  # .csv assumed
            for station in set(sid_file.stations) - self.hidden_stations:
                self.max_data = max(self.max_data,
                                    max(self.sid_files[0].data[0]))
                print(sid_file.startTime, station)
                # Does this station already have a color? if not, reserve one
                if station not in self.color_station:
                    self.color_station[station] = \
                        self.get_station_color(station)
                    if self.color_station[station] is None:
                        # format like 'b-'
                        self.color_station[station] = \
                            color_list[color_idx % len(color_list)] + '-'
                        color_idx += 1
                # Add points to the plot
                self.graph.xaxis.axis_date()
                self.graph.plot(sid_file.timestamp,
                                sid_file.get_station_data(station),
                                self.color_station[station])
        # add the buttons to show/add a station's curve
        for s, c in self.color_station.items():
            btn_color = convert_to_tkinter_color(c)
            station_button = tk.Button(
                self.tk_root, text=s,
                bg=btn_color, activebackground="white")
            station_button.configure(
                command=lambda s=s,
                b=station_button: self.on_click_station(s, b))
            station_button.pack(side='left', padx=1, pady=1)

        noaa_button = tk.Button(self.tk_root, text="NOAA",
                                command=self.on_click_noaa)
        noaa_button.pack(side='left', padx=1, pady=1)
        # other GUI items
        self.statusbar_txt = tk.StringVar()
        self.label = tk.Label(self.tk_root,
                              bd=1, relief=tk.SUNKEN,  # anchor=tk.W,
                              textvariable=self.statusbar_txt,
                              font=('arial', 10, 'normal'), pady=5)
        self.statusbar_txt.set(", ".join(fig_title))
        self.label.pack(fill=tk.X)

        self.calc_ephem()   # calculate the sun rise/set for each file
        self.show_figure()  # add other niceties and show the plot

    def on_click_noaa(self):
        for sid_file in self.sid_files:
            if sid_file.XRAlist:
                sid_file.XRAlist = []  # no longer to be displayed
            elif self.daysList[sid_file.startTime]:
                sid_file.XRAlist = self.daysList[sid_file.startTime]
            else:
                nf = NOAA_flares(sid_file.startTime)
                nf.print_XRAlist()
                self.daysList[sid_file.startTime] = nf.XRAlist
                sid_file.XRAlist = self.daysList[sid_file.startTime]
        self.update_graph()

    def on_click_station(self, station, button):
        """Invert the color of the button. Hide/draw corresponding graph."""
        print("click on", station)
        alt_color = convert_to_tkinter_color(self.color_station[station])
        if station in self.hidden_stations:
            self.hidden_stations.remove(station)
            button.configure(bg=alt_color, activebackground="white")
        else:
            self.hidden_stations.add(station)
            button.configure(bg="white", activebackground=alt_color)
        self.update_graph()

    def show_figure(self):
        """Cosmetics on the figure."""
        current_axes = self.fig.gca()
        current_axes.xaxis.set_minor_locator(matplotlib.dates.HourLocator())
        current_axes.xaxis.set_major_locator(matplotlib.dates.DayLocator())
        current_axes.xaxis.set_major_formatter(ff(m2yyyymmdd))
        current_axes.xaxis.set_minor_formatter(ff(m2hm))
        current_axes.set_xlabel("UTC Time")
        current_axes.set_ylabel("Signal Strength")

        for label in current_axes.xaxis.get_majorticklabels():
            label.set_fontsize(8)
            label.set_rotation(30)  # 'vertical')
            # label.set_horizontalalignment='left'

        for label in current_axes.xaxis.get_minorticklabels():
            label.set_fontsize(12 if len(self.daysList.keys()) == 1 else 8)

        # specific drawings  linked to each sid_file: flares and sunrise/sunset
        bottom_max, top_max = current_axes.get_ylim()
        for sid_file in self.sid_files:
            # for each flare, draw the lines and box with flares intensity
            for eventName, BeginTime, MaxTime, EndTime, Particulars \
                    in sid_file.XRAlist:
                self.graph.vlines(
                    [BeginTime, MaxTime, EndTime], 0,
                    self.max_data, color=['g', 'r', 'y'],
                    linestyles='dotted')
                self.graph.text(
                    MaxTime,
                    self.max_data + (top_max - self.max_data) / 4.0,
                    Particulars, horizontalalignment='center',
                    bbox={
                        'facecolor': 'w',
                        'alpha': 0.5,
                        'fill': True})
            if (sid_file.rising is not None) \
            and (sid_file.setting is not None):
                # draw the rectangles for rising and setting of the sun.
                # Use astronomical twilight
                if sid_file.rising < sid_file.setting:
                    self.graph.axvspan(sid_file.startTime,
                                       sid_file.rising.datetime(),
                                       facecolor='blue', alpha=0.1)
                    self.graph.axvspan(sid_file.setting.datetime(),
                                       max(sid_file.timestamp),
                                       facecolor='blue', alpha=0.1)
                else:
                    self.graph.axvspan(
                        max(sid_file.startTime,
                            sid_file.setting.datetime()),
                        min(sid_file.rising.datetime(),
                            max(sid_file.timestamp)),
                        facecolor='blue', alpha=0.1)

        self.canvas.draw()

    def update_graph(self):
        # Redraw the selected stations on a clear graph
        self.fig.clear()
        self.graph = self.fig.add_subplot(111)
        for sid_file in self.sid_files:
            for station in set(sid_file.stations) - self.hidden_stations:
                print(sid_file.startTime, station)
                # Add points to the plot
                self.graph.xaxis.axis_date()
                self.graph.plot(sid_file.timestamp,
                                sid_file.get_station_data(station),
                                self.color_station[station])
        self.show_figure()

    def calc_ephem(self):
        """Compute the night period of each SidFile using the ephem module."""
        sid_loc = ephem.Observer()
        for sid_file in self.sid_files:
            sid_loc.lon = sid_file.sid_params['longitude']
            sid_loc.lat = sid_file.sid_params['latitude']
            sid_loc.date = sid_file.startTime
            sid_loc.horizon = '-18'  # astronomical twilight
            sid_file.rising = None
            sid_file.setting = None
            try:
                sid_file.rising = \
                    sid_loc.next_rising(ephem.Sun(), use_center=True)
            except Exception as e:
                print(e)
            try:
                sid_file.setting = \
                    sid_loc.next_setting(ephem.Sun(), use_center=True)
            except Exception as e:
                print(e)
            # print(sid_file.filename, sid_file.startTime)
            # print(rising, ephem.localtime(rising))
            # print(setting, ephem.localtime(setting))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-c", "--config",
        dest="cfg_filename",
        type=exist_file,
        default=CONFIG_FILE_NAME,
        help="Supersid configuration file")
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        dest="verbose",
        default=False,
        help="Print more messages.")
    parser.add_argument(
        'file_list',
        metavar='file.csv',
        type=exist_file,
        nargs='+',
        help='file(s) to be plotted')
    args = parser.parse_args()

    # read the configuration file or exit
    cfg = read_config(args.cfg_filename)
    if args.verbose:
        print_config(cfg)

    root = tk.Tk()
    PlotGui(root, cfg, args.file_list)
    root.mainloop()


if __name__ == '__main__':
    main()
