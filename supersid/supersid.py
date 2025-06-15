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
import numpy
import time
import traceback
from numpy import array
from datetime import datetime, timezone
from datetime import time as ti
from matplotlib.mlab import psd as mlab_psd

# SuperSID Package classes
from sidtimer import SidTimer
from sampler import Sampler
from gapless_sampler import GaplessSampler
from config import read_config, CONFIG_FILE_NAME
from logger import Logger
from supersid_common import exist_file, script_relative_to_cwd_relative


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

        
        self.audio_drift_correction = int(0)

        # read the configuration file or exit
        self.config = read_config(config_file)
        self.config["supersid_version"] = self.version
        if viewer is not None:
            self.config['viewer'] = viewer

        self.sample_buffer = array([])
        self.audio_clock_drift_pid_error_ema = 0
        self.audio_clock_drift_pid_sum_error = 0


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
        if self.config['sampler'] == 'gapless':
            self.sampler = GaplessSampler(
                self,
                audio_sampling_rate=self.config['audio_sampling_rate'])
        elif self.config['sampler'] == 'normal':
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

        self.viewer.status_display("Waiting for Timer ... ")
        # Create Timer

        if self.config['sampler'] == 'normal':
            self.timer = SidTimer(self.config['log_interval'], self.on_timer)

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
        subprocess.Popen([
            sys.executable,
            script_relative_to_cwd_relative('ftp_to_stanford.py'),
            '-y',
            '-c',
            script_relative_to_cwd_relative(self.config.filenames[0])])

    def gapless_callback(self, data, audio_time):
        samples_per_log = self.config['log_interval'] * self.sampler.audio_sampling_rate
        systemTime = time.time()
        signal_strengths = []
        try:
            if self.sampler.sampler_ok and data is not None:
                # append the data to the sample buffer
                self.sample_buffer = numpy.append(self.sample_buffer, data)
                
                #Setup any audio clock drift corrections.
                audio_time = audio_time + self.audio_drift_correction
                audio_drift = systemTime - audio_time / self.sampler.audio_sampling_rate

                # If the audio drift is more than 5 seconds, there was a big interrupt
                # skip the entire missing log intervals until the audio clock is within
                # 5 seconds of the system clock.
                if audio_drift >= self.config['log_interval'] or audio_drift <= -self.config['log_interval']:
                    drift_log_intervals = int(audio_drift / self.config['log_interval'])
                    self.audio_drift_correction += drift_log_intervals * samples_per_log
                    audio_time += drift_log_intervals * samples_per_log
                    audio_drift -= drift_log_intervals * self.config['log_interval']

                    # Also clear the pid after a large jump in clock drift.
                    self.audio_clock_drift_pid_error_ema = 0
                    self.audio_clock_drift_pid_sum_error = 0

                audio_time_seconds = audio_time / self.sampler.audio_sampling_rate

                # PID control for small drift correction
                data_sec = len(data) / self.sampler.audio_sampling_rate
                
                # Calculate the ema decay for 1% per second.
                exp = pow(0.99, data_sec)
                
                # Unless you have some really incredible hardware, audio samples can never have been recorded in the future. They can have been
                # recorded in the past. A smaller audio drift will always be more correct than a larger one. The estimate of the drift increases
                # by 1% per second towards the current caculated drift, mostly ignoring any high latency spikes, while closely folllowing the
                # lowest measured latency.
                self.audio_clock_drift_pid_error_ema = min(audio_drift, self.audio_clock_drift_pid_error_ema * exp + audio_drift * (1 - exp))
                
                # The integrated error will accumulate and follow the actual difference in speed between the system and audio clodk. If the
                # audio clock is 10ppm slower than the system clock for example, the sound card will be recording at about 95999hz, and about
                # 5 samples must be dropped from each 5 second period.
                self.audio_clock_drift_pid_sum_error = self.audio_clock_drift_pid_sum_error + self.audio_clock_drift_pid_error_ema * data_sec

                skip_samples = (self.audio_clock_drift_pid_error_ema * self.sampler.audio_sampling_rate * 0.01
                              + self.audio_clock_drift_pid_sum_error * self.sampler.audio_sampling_rate * 0.00001)
                
                # Scale the number of skipped samples with the log interval to make the correction consistent.
                skip_samples = int(skip_samples * self.config['log_interval'] // 5)
                
                #print("Audio Drift: %f Drift Correction: %d Skip Samples: %d Error EMA: %f Error Sum: %f" % (audio_drift, self.audio_drift_correction, skip_samples, self.audio_clock_drift_pid_error_ema, self.audio_clock_drift_pid_sum_error))
                
                # Assume the audio time is the correct time for the last sample recieved
                # determine what the sample for the next log interval is.
                day_start_samples = int(datetime.combine(datetime.fromtimestamp(audio_time_seconds, tz=timezone.utc).date(), ti.min, tzinfo=timezone.utc).timestamp() * self.sampler.audio_sampling_rate)
                end_sample = audio_time - day_start_samples
                start_sample = end_sample - len(self.sample_buffer)
                samples_past_last_log = start_sample % samples_per_log
                samples_to_next_log = samples_per_log - samples_past_last_log

                # If the audio drift correction changed, then the boundry between the samples and the previous log will change.
                # Small samples_to_next_log values will often be values of 1 or 2, but at the start of the recording could
                # be any value. At 192000 hz recording, 4096 samples are needed to do an FFT without error. In very rare cases
                # the first log may include up to 22ms of the previous log interval in order to avoid any chance of trying
                # to compute an FFT with too little data.
                if(samples_to_next_log < self.sampler.NFFT + skip_samples):
                    samples_to_next_log += samples_per_log

                # Calculate the timestamp the current log interval started at.
                log_time = round((audio_time - len(self.sample_buffer) + samples_to_next_log - samples_per_log) / self.sampler.audio_sampling_rate)
                
                # Reduce samples to next log by audio correction
                samples_to_next_log -= skip_samples
                samples_needed = samples_to_next_log - len(self.sample_buffer)

                if samples_needed <= 0:
                    log_datetime = datetime.fromtimestamp(log_time, tz=timezone.utc)
                    log_samples = self.sample_buffer[:samples_to_next_log]
                    self.sample_buffer = self.sample_buffer[samples_to_next_log:]

                    # Correct the audio time to include the skipped samples.
                    self.audio_drift_correction += skip_samples

                    Pxx, freqs = self.get_psd(log_samples.reshape(len(log_samples), data.shape[1]), self.sampler.NFFT,
                                        self.sampler.audio_sampling_rate)
                    if Pxx is not None:
                        self.viewer.update_psd(Pxx, freqs)
                        for channel, binSample in zip(
                                self.sampler.monitored_channels,
                                self.sampler.monitored_bins):
                            signal_strengths.append(Pxx[channel][binSample])
                        # in case of an exception,
                        # signal_strengths may not have the expected length
                    while len(signal_strengths) < len(self.sampler.monitored_bins):
                        signal_strengths.append(0.0)
                        
                    # do we need to save some files (hourly) or switch to a new day?
                    if ((log_datetime.minute == 0) and
                            (log_datetime.second < self.config['log_interval'])):
                        if self.config['hourly_save'] == 'YES':
                            fileName = "hourly_current_buffers.raw.ext.%s.csv" % (
                                self.logger.sid_file.sid_params['utc_starttime'][:10])
                            self.save_current_buffers(filename=fileName,
                                            log_type='raw',
                                            log_format='supersid_extended')
                        # a new day! 
                        if log_datetime.hour == 0:
                            # use log_type and log_format requested by the user
                            # in the .cfg
                            self.save_current_buffers(log_type=self.config['log_type'],
                                                    log_format=self.config['log_format'])
                            self.clear_all_data_buffers()
                            self.ftp_to_stanford()



                    # Save signal strengths into memory buffers
                    # prepare message for status bar
                    current_index = (log_datetime.hour * 3600
                                   + log_datetime.minute * 60
                                   + log_datetime.second) // self.config['log_interval']

                    message = log_datetime.strftime("%Y-%m-%d %H:%M:%S") + " [%d]  " % current_index+ " Audio Sync: {:.3f}s".format(audio_drift) + "  Correction: %d samples  " % -self.audio_drift_correction
                    for station, strength in zip(self.config.stations,
                                                signal_strengths):
                        station['raw_buffer'][current_index] = strength
                        message += station['call_sign'] + "=%f " % strength
                    self.logger.sid_file.timestamp[current_index] = log_datetime

                    # end of this thread/need to handle to View to display
                    # captured data & message
                    self.viewer.status_display(message)


        except IndexError as idxerr:
            print("Index Error:", idxerr)
            print("Data len:", len(data))
            tb = traceback.extract_tb(idxerr.__traceback__)
            print(tb)
        except TypeError as err_te:
            print("Warning:", err_te)
            tb = traceback.extract_tb(err_te.__traceback__)
            print(tb)
        except Exception as err:
            print("Error:", err)
            tb = traceback.extract_tb(err.__traceback__)
            print(tb)

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
                    for channel, binSample in zip(
                            self.sampler.monitored_channels,
                            self.sampler.monitored_bins):
                        signal_strengths.append(pxx[channel][binSample])
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
        if ((self.timer.utc_now.minute == 0) and
                (self.timer.utc_now.second < self.config['log_interval'])):
            if self.config['hourly_save'] == 'YES':
                file_name = (f"hourly_current_buffers.raw.ext."
                             f"{self.logger.sid_file.sid_params['utc_starttime'][:10]}.csv")
                print("Saving hourly buffers to", file_name)
                self.save_current_buffers(filename=file_name,
                                          log_type='raw',
                                          log_format='supersid_extended')
            # a new day!
            if self.timer.utc_now.hour == 0:
                # use log_type and log_format requested by the user
                # in the .cfg
                self.save_current_buffers(log_type=self.config['log_type'],
                                          log_format=self.config['log_format'])
                self.clear_all_data_buffers()
                self.ftp_to_stanford()
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
            overlap = 0
            if self.config['overlap']:
                overlap = nfft // 2

            pxx = {}
            freqs = []

            for channel in range(self.config['Channels']):
                pxx[channel], freqs = \
                    mlab_psd(data[:, channel], NFFT=nfft, Fs=fs, noverlap=overlap)
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
            if self.config['sampler'] == 'normal':
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
