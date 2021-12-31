#!/usr/bin/env python3
"""SuperSID class is the Controller.

supersid.py
version 1.3
Segregation MVC

First, it reads the .cfg file specified on the command line
Then it creates its necessary elements:
    - Model: Logger, Sampler
    - Viewer: Viewer
    using the parameters read in the .cfg file
    Finally, it launches an infinite loop to wait for events:
    - User input (graphic or text)
    - Timer for sampling
    - <still missing> network management with client-server protocol
"""
import sys
import os.path
import argparse

# matplotlib ONLY used in Controller for its PSD function, not for any graphic
from matplotlib.mlab import psd as mlab_psd

# SuperSID Package classes
from sidtimer import SidTimer
from sampler import Sampler
from config import readConfig, CONFIG_FILE_NAME
from logger import Logger
from supersid_common import exist_file


class SuperSID():
    """Main class which creates all other objects.

    In CMV pattern, this is the Controller.
    """

    running = False  # class attribute indicates the SID application running

    def __init__(self, config_file, read_file=None, viewer=None):
        self.version = "EG 1.4 20150801"
        self.timer = None
        self.sampler = None
        self.viewer = None

        # read the configuration file or exit
        self.config = readConfig(args.cfg_filename)
        self.config["supersid_version"] = self.version
        if viewer is not None:
            self.config['viewer'] = viewer

        # Create Logger -
        # Logger will read an existing file if specified
        # as -r|--read script argument
        self.logger = Logger(self, read_file)
        if 'utc_starttime' not in self.config:
            self.config['utc_starttime'] = self.logger.sid_file.sid_params["utc_starttime"]

        # Create the viewer based on the .cfg specification (or set default):
        # Note: the list of Viewers can be extended provided they implement
        # the same interface
        if self.config['viewer'] == 'wx':
            # GUI Frame to display real-time VLF Spectrum based on wxPython
            # special case: 'wx' module might not be installed (text mode only)
            try:
                from wxsidviewer import wxSidViewer
                self.viewer = wxSidViewer(self)
                wx_imported = True
            except ImportError:
                print("'wx' module not imported.")
                wx_imported = False
        elif self.config['viewer'] == 'tk':
            # GUI Frame to display real-time VLF Spectrum based on
            # tkinter
            from tksidviewer import tkSidViewer
            self.viewer = tkSidViewer(self)
        elif self.config['viewer'] == 'text':
            # Lighter text version a.k.a. "console mode"
            from textsidviewer import textSidViewer
            self.viewer = textSidViewer(self)
        else:
            print("ERROR: Unknown viewer", sid.config['viewer'])
            sys.exit(2)

        # Assign desired PSD function for calculation after capture
        # currently: using matplotlib's psd
        if ((self.config['viewer'] == 'wx' and wx_imported)
                or self.config['viewer'] == 'tk'):
            # calculate psd and draw result in one call
            self.psd = self.viewer.get_psd
        else:
            self.psd = mlab_psd             # calculation only

        # calculate Stations' buffer_size
        self.buffer_size = int(24*60*60 / self.config['log_interval'])

        # Create Sampler to collect audio buffer (sound card or other server)
        self.sampler = Sampler(self,
                               audio_sampling_rate=self.config['audio_sampling_rate'])
        if not self.sampler.sampler_ok:
            self.close()
            sys.exit(3)
        else:
            self.sampler.set_monitored_frequencies(self.config.stations)

        # Link the logger.sid_file.data buffers to the config.stations
        for ibuffer, station in enumerate(self.config.stations):
            station['raw_buffer'] = self.logger.sid_file.data[ibuffer]

        # Create Timer
        self.viewer.status_display("Waiting for Timer ... ")
        self.timer = SidTimer(self.config['log_interval'], self.on_timer)

    def clear_all_data_buffers(self):
        """Clear the current memory buffers and pass to the next day."""
        self.logger.sid_file.clear_buffer(next_day=True)

    def on_timer(self):
        """Call when timer expires.

        Triggered by SidTimer every 'log_interval' seconds
        """
        # current_index is the position in the buffer calculated
        # from current UTC time
        current_index = self.timer.data_index
        utc_now = self.timer.utc_now

        # Get new data and pass them to the View
        message = "%s  [%d]  Capturing data..." % (self.timer.get_utc_now(),
                                                   current_index)
        self.viewer.status_display(message, level=1)
        signal_strengths = []
        try:
            data = self.sampler.capture_1sec()  # return list of signal strength, may set sampler_ok = False
            if self.sampler.sampler_ok:
                Pxx, freqs = self.psd(data, self.sampler.NFFT,
                                      self.sampler.audio_sampling_rate)
                for binSample in self.sampler.monitored_bins:
                    signal_strengths.append(Pxx[binSample])
        except IndexError as idxerr:
            print("Index Error:", idxerr)
            print("Data len:", len(data))
        except TypeError as err_te:
            print("Warning:", err_te)
        
        # in case of an exception, signal_strengths may not have the expected length
        while len(signal_strengths) < len(self.sampler.monitored_bins):
            signal_strengths.append(0.0)

        # do we need to save some files (hourly) or switch to a new day?
        if self.timer.utc_now.minute == 0 and self.timer.utc_now.second < self.config['log_interval']:
            if self.config['hourly_save'] == 'YES':
                fileName = "hourly_current_buffers.raw.ext.%s.csv" % (
                    self.logger.sid_file.sid_params['utc_starttime'][:10])
                self.save_current_buffers(filename=fileName,
                                          log_type='raw',
                                          log_format='supersid_extended')
            # a new day!
            if self.timer.utc_now.hour == 0:
                # use log_type and log_format(s) requested by the user
                # in the .cfg
                for log_format in self.config['log_format'].split(','):
                    self.save_current_buffers(log_type=self.config['log_type'],
                                              log_format=log_format)
                self.clear_all_data_buffers()
        # Save signal strengths into memory buffers
        # prepare message for status bar
        message = self.timer.get_utc_now() + "  [%d]  " % current_index
        for station, strength in zip(self.config.stations,
                                     signal_strengths):
            station['raw_buffer'][current_index] = strength
            message += station['call_sign'] + "=%f " % strength
        self.logger.sid_file.timestamp[current_index] = utc_now

        # end of this thread/need to handle to View to display
        # captured data & message
        self.viewer.status_display(message, level=2)

    def save_current_buffers(self, filename='', log_type='raw',
                             log_format='both'):
        """Save buffer data from logger.sid_file.

        log_type = raw or filtered
        log_format = sid_format
                    | sid_extended
                    | supersid_format
                    | supersid_extended
                    | both
                    | both_extended
        """
        filenames = []
        if log_format.startswith('both') or log_format.startswith('sid'):
            # filename is '' to ensure one file per station
            fnames = self.logger.log_sid_format(self.config.stations, '',
                                                log_type=log_type,
                                                extended=log_format.endswith('extended'))
            filenames += fnames
        if log_format.startswith('both') or log_format.startswith('supersid'):
            fnames = self.logger.log_supersid_format(self.config.stations,
                                                     filename,
                                                     log_type=log_type,
                                                     extended=log_format.endswith('extended'))
            filenames += fnames
        return filenames

    def on_close(self):
        self.close()

    def run(self, wx_app=None):
        """Start the application as infinite loop accordingly to need."""
        self.__class__.running = True
        self.viewer.run()

    def close(self):
        """Call all necessary stop/close functions of children objects."""
        self.__class__.running = False
        if self.sampler:
            self.sampler.close()
        if self.timer:
            self.timer.stop()
        if self.viewer:
            self.viewer.close()

    def about_app(self):
        """Return a text indicating  information on the app, incl, version."""
        msg = ("This program is designed to detect Sudden Ionospheric "
               "Disturbances (SID), which are caused by a blast of intense "
               "X-ray radiation when there is a Solar Flare on the Sun.\n\n"
               "Controller: " + self.version + "\n"
               + "Sampler: " + self.sampler.version + "\n"
               "Timer: " + self.timer.version + "\n"
               "Config: " + self.config.version + "\n"
               "Logger: " + self.logger.version + "\n"
               "Sidfile: " + self.logger.sid_file.version + "\n"
               "Viewer: " + self.viewer.version + "\n"
               "\n\nOriginal Author: Eric Gibert  ericgibert@yahoo.fr"
               "\nAdditions by: Steve Berl <steveberl@gmail.com>"
               "\n\nVisit http://solar-center.stanford.edu/SID/sidmonitor/ "
               "for more information.")

        return msg


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-r", "--read", dest="filename", required=False,
                        type=exist_file,
                        help="Read raw file and continue recording")
    parser.add_argument("-c", "--config", dest="cfg_filename",
                        type=exist_file,
                        default=CONFIG_FILE_NAME,
                        help="Supersid configuration file")
    parser.add_argument("-v", "--viewer",
                        default=None,
                        choices=['text', 'tk', 'wx'],
                        help="viewer (overrides viewer setting in the configuration file)")
    args = parser.parse_args()

    sid = SuperSID(config_file=args.cfg_filename, read_file=args.filename, viewer=args.viewer)
    sid.run()
    sid.close()
