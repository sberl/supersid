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
import subprocess
import time
from datetime import datetime, timezone
from matplotlib.mlab import psd as mlab_psd

# SuperSID Package classes
from sidtimer import SidTimer
from supersid_sampler import Sampler
from supersid_config import read_config, CONFIG_FILE_NAME
from supersid_logger import Logger
from supersid_common import exist_file, script_relative_to_cwd_relative, is_script

class SuperSID:
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
        self.config = read_config(config_file)
        self.config["supersid_version"] = self.version
        if viewer is not None:
            self.config['viewer'] = viewer

        # command line parameter -r/--read has precedence over automatic read
        if read_file is None:
            # if there are hourly saves ...
            if self.config['hourly_save'] == 'YES':
                # ... figure out the file name ...
                utcnow = datetime.now(timezone.utc)
                utc_starttime = f"{utcnow.year}-{utcnow.month:02d}-{utcnow.day:02d} 00:00:00"
                file_name = (f"{self.config['data_path']}"
                             f"hourly_current_buffers.raw.ext.{utc_starttime[:10]}.csv")
                # ... check the existence ...
                if os.path.isfile(file_name):
                    # ... and force reading
                    read_file = file_name

        # Create Logger -
        # Logger will read an existing file if specified
        # as -r|--read script argument
        self.logger = Logger(self, read_file)
        if 'utc_starttime' not in self.config:
            self.config['utc_starttime'] = \
                self.logger.sid_file.sid_params["utc_starttime"]

        # Create the viewer based on the .cfg specification (or set default):
        # Note: the list of Viewers can be extended provided they implement
        # the same interface
        if self.config['viewer'] == 'tk':
            # GUI Frame to display real-time VLF Spectrum based on
            # tkinter
            from tksidviewer import tkSidViewer # pylint: disable=import-outside-toplevel
            self.viewer = tkSidViewer(self)
        elif self.config['viewer'] == 'text':
            # Lighter text version a.k.a. "console mode"
            from textsidviewer import textSidViewer # pylint: disable=import-outside-toplevel
            self.viewer = textSidViewer(self)
        else:
            print("ERROR: Unknown viewer", self.config['viewer'])
            sys.exit(2)

        # calculate Stations' buffer_size
        self.buffer_size = int(24*60*60 / self.config['log_interval'])

        # Create Sampler to collect audio buffer (sound card or other server)
        self.sampler = Sampler(
            self,
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
        self.hour = self.timer.utc_now.hour     # detection of the hour change

    def clear_all_data_buffers(self):
        """Clear the current memory buffers and pass to the next day."""
        self.logger.sid_file.clear_buffer(next_day=True)

    def ftp_to_stanford(self):
        """
        Call 'ftp_to_stanford.py -y' in a separate process to prevent
        interference with data capture.

        As of today, the -y option of ftp_to_stanford.py expects to find
        a supersid formated file of yesterday with the name
        <data_path>/<site_name>_yyyy-mm-dd.csv.

        Files with this naming scheme are created with either one of
            log_format = supersid_format
            log_format = supersid_extended
            log_format = both
            log_format = both_extended

        These configurations are not suitable for 'ftp_to_stanford.py -y':
            log_format = sid_format
            log_format = sid_extended

        The files for the upload are generated into the 'local_tmp' folder
        of the [FTP] section. By default, this is the directory '../outgoing'.

        Automatic ftp upload is performed only if 'automatic_upload = yes'
        is set.

        """
        if is_script():
            cmd = [sys.executable,
                    script_relative_to_cwd_relative('ftp_to_stanford.py')]
        else:
            cmd = [script_relative_to_cwd_relative('ftp_to_stanford.exe')]
        subprocess.Popen(cmd + [
            '-y',
            '-c',
            script_relative_to_cwd_relative(self.config.filenames[0])])

    def on_timer(self):
        """Call when timer expires.

        Triggered by SidTimer every 'log_interval' seconds
        """
        # current_index is the position in the buffer calculated
        # from current UTC time
        current_index = self.timer.data_index
        utc_now = self.timer.utc_now

        # Get new data and pass them to the View
        message = f"{self.timer.get_utc_now()}  [{current_index}]  Capturing data..."
        self.viewer.status_display(message)
        signal_strengths = []
        data = []
        try:
            # capture_1sec() returns list of signal strength,
            # may set sampler_ok = False
            data = self.sampler.capture_1sec()

            if self.sampler.sampler_ok:
                pxx, freqs = self.get_psd(data, self.sampler.NFFT,
                                      self.sampler.audio_sampling_rate)
                if pxx is not None:
                    self.viewer.update_psd(pxx, freqs)
                    for channel, bin_sample in zip(
                            self.sampler.monitored_channels,
                            self.sampler.monitored_bins):
                        signal_strengths.append(pxx[channel][bin_sample])
        except IndexError as idxerr:
            print("Index Error:", idxerr)
            print("Data len:", len(data))
        except TypeError as err_te:
            print("Warning:", err_te)

        # in case of an exception,
        # signal_strengths may not have the expected length
        while len(signal_strengths) < len(self.sampler.monitored_bins):
            signal_strengths.append(0.0)

        # do we need to save some files (hourly) or switch to a new day?
        if self.hour != self.timer.utc_now.hour:    # Did the hour change?
            self.hour = self.timer.utc_now.hour     # Yes, it changed!
            if self.config['hourly_save'] == 'YES':
                file_name = (f"hourly_current_buffers.raw.ext."
                             f"{self.logger.sid_file.sid_params['utc_starttime'][:10]}.csv")

                time_info = f"{self.timer.utc_now} saving {file_name}"
                t_start = time.time()
                self.save_current_buffers(filename=file_name,
                                          log_type='raw',
                                          log_format='supersid_extended')
                print(f"{time_info} in {time.time() - t_start:0.1f} sec")

            # a new day!
            if self.timer.utc_now.hour == 0:
                # use log_type and log_format requested by the user
                # in the .cfg

                time_info = f"{datetime.now(timezone.utc)} saving yesterdays files "
                t_start = time.time()
                self.save_current_buffers(log_type=self.config['log_type'],
                                          log_format=self.config['log_format'])
                print(f"{time_info} in {time.time() - t_start:0.1f} sec")

                self.clear_all_data_buffers()

                time_info = f"{datetime.now(timezone.utc)} ftp to Stanford "
                t_start = time.time()
                self.ftp_to_stanford()
                print(f"{time_info} in {time.time() - t_start:0.1f} sec")

        # Save signal strengths into memory buffers
        # prepare message for status bar
        message = f"{self.timer.get_utc_now()}  [{current_index}]  "
        for station, strength in zip(self.config.stations,
                                     signal_strengths):
            station['raw_buffer'][current_index] = strength
            message += f"{station['call_sign']}={strength:.4f} "
        self.logger.sid_file.timestamp[current_index] = utc_now

        # end of this thread/need to handle to View to display
        # captured data & message
        self.viewer.status_display(message)

    def get_psd(self, data, nfft, fs):
        """Call 'psd', calculates the spectrum."""
        try:
            pxx = {}
            freqs = []
            for channel in range(self.config['Channels']):
                pxx[channel], freqs = \
                    mlab_psd(data[:, channel], NFFT=nfft, Fs=fs)
        except RuntimeError as err_re:
            print("Warning:", err_re)
            pxx, freqs = None, None
        return pxx, freqs

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
            fnames = self.logger.log_sid_format(
                self.config.stations,
                log_type=log_type,
                extended=log_format.endswith('extended'))
            filenames += fnames
        if log_format.startswith('both') or log_format.startswith('supersid'):
            fnames = self.logger.log_supersid_format(
                self.config.stations,
                filename,
                log_type=log_type,
                extended=log_format.endswith('extended'))
            filenames += fnames
        return filenames

    def on_close(self):
        """Handle the close event of the application."""
        self.close()

    def run(self):
        """Start the application as infinite loop accordingly to need."""
        self.__class__.running = True
        self.viewer.run()

    def close(self):
        """Call all necessary stop/close functions of children objects."""
        self.__class__.running = False
        if self.config['hourly_save'] == 'YES':
            file_name = (f"hourly_current_buffers.raw.ext."
                        f"{self.logger.sid_file.sid_params['utc_starttime'][:10]}.csv")
            self.save_current_buffers(filename=file_name,
                                      log_type='raw',
                                      log_format='supersid_extended')
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
               "\n\nVisit https://solar-center.stanford.edu/SID/sidmonitor/ "
               "for more information.")

        return msg


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-r", "--read", dest="filename", required=False,
        type=exist_file,
        help="Read raw file and continue recording")
    parser.add_argument(
        "-c", "--config", dest="cfg_filename",
        type=exist_file,
        default=CONFIG_FILE_NAME,
        help="Supersid configuration file")
    parser.add_argument(
        "-v", "--viewer",
        default=None,
        choices=['text', 'tk'],
        help="viewer (overrides viewer setting in the configuration file)")
    args = parser.parse_args()

    sid = SuperSID(
        config_file=args.cfg_filename,
        read_file=args.filename,
        viewer=args.viewer)
    sid.run()
    sid.close()
