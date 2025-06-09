#!/usr/bin/env python3
"""
GaplessSampler is a more noise resistant audio sampler.

Also handles calculating PSD, extracting signal strengths at monitored
frequencies, saving spectrum and spectrogram (image) to png file

The GaplessSampler class will use an audio 'device' to continuously capture
sound and return 1 second slices.
This 'device' can be a local sound card:
     - controlled by sounddevice or pyaudio on Windows or other system
     - controlled by alsaaudio on Linux
    or this 'device' can be a remote server
     - client mode accessing server thru TCP/IP socket (to be implemented)

    All these 'devices' must implement:
     - __init__: open the 'device' for future capture
     - update: When called the sampler must read the audio buffers and
        accumulate them in a local array. If there are more than 1 second
        of samples, it should return a tuple containing the data as an
        array of 'audio_sampling rate' integers and the current audio time.
     - close: close the 'device'
"""
import sys
import time
import argparse
import traceback
import numpy
import datetime
from struct import unpack as st_unpack
from numpy import array
from matplotlib.mlab import psd as mlab_psd
from datetime import timezone

from config import FREQUENCY, S16_LE, S24_3LE, S32_LE


def get_peak_freq(data, audio_sampling_rate):
    # NFFT = 1024 for 44100 and 48000,
    #        2048 for 96000,
    #        4096 for 192000
    # -> the frequency resolution is constant
    NFFT = max(1024, 1024 * audio_sampling_rate // 48000)
    Pxx, freqs = mlab_psd(data, NFFT, audio_sampling_rate)
    m = max(Pxx)
    if m == min(Pxx):
        peak_freq = 0
    else:
        pos = [i for i, j in enumerate(Pxx) if j == m]
        peak_freq = int(freqs[pos][0])
    return peak_freq


audioModule = []
try:
    import alsaaudio  # for Linux direct sound capture
    audioModule.append("alsaaudio")

    def alsaaudio_test(device, sampling_rate, format, channels, periodsize):
        print()
        try:
            print(
                "Accessing '{}' at {} Hz via alsaaudio "
                "format {}, channels {}..."
                .format(device, sampling_rate, format, channels))
            sc = alsaaudio_soundcard(
                '',
                device,
                sampling_rate,
                format,
                channels,
                periodsize)
            sc.info()
            return True
        except alsaaudio.ALSAAudioError as err:
            print(err)
            return False

    class alsaaudio_soundcard():
        """Sampler for an ALSA audio device."""
        # map ALSA format string to module format
        FORMAT_MAP = {
            # Signed 16 bit samples stored in 2 bytes, Little Endian byte order
            S16_LE: alsaaudio.PCM_FORMAT_S16_LE,

            # Signed 24 bit samples stored in 3 bytes, Little Endian byte order
            S24_3LE: alsaaudio.PCM_FORMAT_S24_3LE,

            # Signed 32 bit samples stored in 4 bytes, Little Endian byte order
            S32_LE: alsaaudio.PCM_FORMAT_S32_LE,
        }

        # map ALSAO format string to length of one sample in bytes
        FORMAT_LENGTHS = {
            S16_LE: 2,
            S24_3LE: 3,
            S32_LE: 4,
        }

        def __init__(
                self,
                card,
                device,
                audio_sampling_rate,
                format,
                channels,
                periodsize):
            """
            Initialize the ALSA audio sampler.
            card is deprecated but still present for backward compatibility
            device is preferred
            """

            # time to capture 1 sec of data excluding the format conversion
            self.duration = None

            self.format = format
            self.channels = channels
            self.audio_sampling_rate = audio_sampling_rate
            if card != '':
                # deprecated configuration keyword Card, use Device instead
                # alsaaudio.PCM(card=card) deprecated since pyalsaaudio 0.8.0
                # the device name would be built as 'default:CARD=' + card
                # it has been observed, that default fails often,
                # thus guessing the device name as 'sysdefault:CARD=' + card
                device = 'sysdefault:CARD=' + card
                print(
                    "alsaaudio card '{}', "
                    "sampling rate {}, "
                    "format {}, "
                    "channels {}, "
                    "periodsize {}"
                    .format(
                        card,
                        audio_sampling_rate,
                        format,
                        channels,
                        periodsize))

                self.name = "alsaaudio Device guessed as '{}'".format(device)

                self.inp = alsaaudio.PCM(alsaaudio.PCM_CAPTURE,
                                         alsaaudio.PCM_NORMAL,
                                         channels=self.channels,
                                         rate=audio_sampling_rate,
                                         format=self.FORMAT_MAP[self.format],
                                         periodsize=periodsize,
                                         periods=256,
                                         device=device)
                
            else:
                print(
                    "alsaaudio device '{}', "
                    "sampling rate {}, "
                    "format {}, "
                    "channels {}, "
                    "periodsize {}"
                    .format(
                        device,
                        audio_sampling_rate,
                        format,
                        channels,
                        periodsize))
                self.name = "alsaaudio '{}'".format(device)

                self.inp = alsaaudio.PCM(alsaaudio.PCM_CAPTURE,
                                         alsaaudio.PCM_NORMAL,
                                         channels=self.channels,
                                         rate=audio_sampling_rate,
                                         format=self.FORMAT_MAP[self.format],
                                         periodsize=periodsize,
                                         periods=256,
                                         device=device)
            
            
            self.audioTime = int(time.time() * audio_sampling_rate)
                
        def update(self):
            #print("here")
            if self.inp.avail() == 0:
                return (None, None)
            (length, raw_data) = self.inp.read()
            if length < 0:
                print("Buffer overflowed")
            unpacked_data = None
            if self.format == S16_LE:
                unpacked_data = array(st_unpack(
                    "<%ih" % (len(raw_data)/2),
                    raw_data))
            elif self.format == S24_3LE:
                unpacked_data = []
                for i in range(int(len(raw_data)/2)):
                    chunk = raw_data[i*3:i*3+3]
                    unpacked_data.append(int.from_bytes(chunk, byteorder='little', signed=True))
            elif self.format == S32_LE:
                unpacked_data = array(st_unpack(
                    "<%ii" % (len(raw_data)/4),
                    raw_data))
                
            self.audioTime += int(len(unpacked_data / self.channels))
            unpacked_data = array(unpacked_data)
            return (unpacked_data.reshape(int(len(unpacked_data) / self.channels), self.channels), self.audioTime)
            
        def close(self):
            self.inp.close()

        def info(self):
            print(self.name, "at", self.audio_sampling_rate, "Hz")
            try:
                one_sec = array([])
                tries = 0
                while tries < 20 and len(one_sec) < self.audio_sampling_rate:
                    (data, audio_time) = self.update()
                    if data is not None:
                        one_sec = numpy.append(one_sec, data)
                    tries += 1
                    time.sleep(0.1)
                if len(one_sec) < self.audio_sampling_rate:
                    print("The audio device produced no audio.")
                one_sec = one_sec[:self.audio_sampling_rate]
                one_sec = one_sec.reshape(self.audio_sampling_rate, self.channels)
                text_data = ""
                text_vector_sum = "Vector sum"
                peak_freq = []
                for channel in range(self.channels):
                    channel_one_sec = one_sec[:, channel]
                    peak_freq.append(get_peak_freq(
                        channel_one_sec,
                        self.audio_sampling_rate))
                    text_data += "[{} ... {}], ".format(
                        " ".join(str(i) for i in channel_one_sec[:5]),
                        " ".join(str(i) for i in channel_one_sec[-5:]))
                    text_vector_sum += " {},".format(channel_one_sec.sum())
                print(
                    "{:6d} "
                    "{} "
                    "read from {}, "
                    "shape {}, "
                    "format {}, "
                    "channel {}, "
                    "peak freq {} Hz"
                    .format(
                        len(channel_one_sec),
                        type(channel_one_sec[0]),
                        self.name,
                        one_sec.shape,
                        self.format,
                        channel,
                        peak_freq))
                print(text_data)
                print(text_vector_sum)
            except Exception as err:
                print("Exception", type(err), err)

except ImportError:
    pass


try:
    # for Linux and Windows http://python-sounddevice.readthedocs.org
    import sounddevice
    audioModule.append("sounddevice")

    def sounddevice_test(device, sampling_rate, format, channels):
        print()
        try:
            print(
                "Accessing '{}' at {} Hz via sounddevice "
                "format {}, channels {}..."
                .format(device, sampling_rate, format, channels))
            sc = sounddevice_soundcard(device, sampling_rate, format, channels)
            sc.info()
            return True
        except Exception as err:
            print(err)
            return False

    class sounddevice_soundcard():
        # map ALSA format string to module format
        FORMAT_MAP = {
            # Signed 16 bit samples stored in 2 bytes, Little Endian byte order
            S16_LE: 'int16',

            # Signed 24 bit samples stored in 3 bytes, Little Endian byte order
            S24_3LE: 'int24',

            # Signed 32 bit samples stored in 4 bytes, Little Endian byte order
            S32_LE: 'int32',
        }

        def __init__(
                self,
                device_name,
                audio_sampling_rate,
                format,
                channels):
            print(
                "sounddevice device '{}', "
                "sampling rate {}, "
                "format {}, "
                "channels {}"
                .format(
                    device_name,
                    audio_sampling_rate,
                    format,
                    channels))

            # time to capture 1 sec of data excluding the format conversion
            self.duration = None

            self.audio_sampling_rate = audio_sampling_rate
            self.device_name = device_name
            self.format = format
            self.channels = channels
            sounddevice.default.samplerate = audio_sampling_rate
            sounddevice.default.device = self.get_device_by_name(
                self.device_name)
            sounddevice.default.channels = self.channels
            sounddevice.default.latency = 'high'
            sounddevice.default.dtype = self.FORMAT_MAP[format]
            self.name = "sounddevice '{}'".format(self.device_name)
            self.stream = sounddevice.InputStream()
            self.stream.start()
            self.audioTime = int(time.time() * audio_sampling_rate)


            

        @staticmethod
        def query_input_devices():
            input_device_names = []
            for device_info in sounddevice.query_devices():
                # we are interrested only in input devices
                if device_info['max_input_channels'] > 0:
                    hostapi_name = sounddevice.query_hostapis(
                        device_info['hostapi'])['name']
                    input_device_names.append(
                        "{}: {}"
                        .format(hostapi_name, device_info['name']))
            return input_device_names

        @staticmethod
        def get_device_by_name(device_name):
            if str == type(device_name):
                separator_pos = device_name.find(':')
                hostapi = sounddevice_soundcard.get_hostapi_by_name(
                    device_name[0:separator_pos])
                name = device_name[separator_pos+1:].strip()
                for i, device_info in enumerate(sounddevice.query_devices()):
                    if ((device_info['hostapi'] == hostapi) and
                            (device_info['name'] == name)):
                        return i
            print(
                "Warning: sounddevice Device '{}' not found"
                .format(device_name))
            return None

        @staticmethod
        def get_hostapi_by_name(hostapi_name):
            hostapis = sounddevice.query_hostapis()
            for index, host_api_info in enumerate(hostapis):
                if host_api_info['name'] == hostapi_name:
                    return index
            print(
                "Warning: sounddevice Host API '{}' not found"
                .format(hostapi_name))
            return None

        def update(self):
            #print("here")
            try:
                if self.stream.read_available == 0:
                    return (None, None)
                if self.format in [S16_LE, S32_LE]:
                    (data, overflow) = self.stream.read(self.stream.read_available)
                    if overflow:
                        print("Buffer overflowed")
                    self.audioTime += int(len(data) / self.channels)
                    return (data.reshape(int(len(data) / self.channels), self.channels), self.audioTime)
                else:
                    raise ValueError("sounddevice can only use formats S16_LE or S32_LE")
            except sounddevice.PortAudioError as err:
                print("Error reading device", self.name)
                print(err)
                return(None, None)

        def close(self):
            self.stream.close()

        def info(self):
            print(self.name, "at", self.audio_sampling_rate, "Hz")

            # index 0 of sounddevice.default.device is the input device
            assert (sounddevice.default.device[0] ==
                    self.get_device_by_name(self.device_name)), \
                "get_device_by_name() delivered an unexpected device"

            try:
                one_sec = array([])
                tries = 0
                while tries < 20 and len(one_sec) < self.audio_sampling_rate:
                    (data, audio_time) = self.update()
                    if data is not None:
                        one_sec = numpy.append(one_sec, data)
                    tries += 1
                    time.sleep(0.1)
                if len(one_sec) < self.audio_sampling_rate:
                    print("The audio device generated no audio")
                    return
                self.stream.close()
                one_sec = one_sec[:self.audio_sampling_rate]
                one_sec = one_sec.reshape(self.audio_sampling_rate, 1)
                text_data = ""
                text_vector_sum = "Vector sum"
                peak_freq = []
                for channel in range(self.channels):
                    channel_one_sec = one_sec[:, channel]
                    peak_freq.append(get_peak_freq(
                        channel_one_sec, self.audio_sampling_rate))
                    text_data += "[{} ... {}], ".format(
                        " ".join(str(i) for i in channel_one_sec[:5]),
                        " ".join(str(i) for i in channel_one_sec[-5:]))
                    text_vector_sum += " {},".format(channel_one_sec.sum())
                print(
                    "{:6d} "
                    "{} "
                    "read from {}, "
                    "shape {}, "
                    "format {}, "
                    "channel {}, "
                    "peak freq {} Hz"
                    .format(
                        len(channel_one_sec),
                        type(channel_one_sec[0]),
                        self.name,
                        one_sec.shape,
                        self.format,
                        channel,
                        peak_freq))
                print(text_data)
                print(text_vector_sum)
            except Exception as err:
                print("Exception", type(err), err)
                tb = traceback.extract_tb(err.__traceback__)
                print(tb)

except ImportError:
    pass


try:
    import pyaudio  # for Linux with jackd OR windows
    audioModule.append("pyaudio")

    def pyaudio_test(device, sampling_rate, format, channels):
        print()
        try:
            print(
                "Accessing '{}' at {} Hz via pyaudio "
                "format {}, channels {}, ..."
                .format(device, sampling_rate, format, channels))
            sc = pyaudio_soundcard(device, sampling_rate, format, channels)
            sc.info()
            return True
        except Exception as err:
            print(err)
            return False

    class pyaudio_soundcard():
        # map ALSA format string to module format
        FORMAT_MAP = {
            # Signed 16 bit samples stored in 2 bytes, Little Endian byte order
            S16_LE: pyaudio.paInt16,

            # Signed 24 bit samples stored in 3 bytes, Little Endian byte order
            S24_3LE: pyaudio.paInt24,

            # Signed 32 bit samples stored in 4 bytes, Little Endian byte order
            S32_LE: pyaudio.paInt32,
        }

        # map ALSAO format string to length of one sample in bytes
        FORMAT_LENGTHS = {
            S16_LE: 2,
            S24_3LE: 3,
            S32_LE: 4,
        }

        def __init__(
                self,
                device_name,
                audio_sampling_rate,
                format,
                channels):
            print(
                "pyaudio device '{}', "
                "sampling rate {}, "
                "format {}, "
                "channels {}"
                .format(
                    device_name,
                    audio_sampling_rate,
                    format,
                    channels))

            # time to capture 1 sec of data excluding the format conversion
            self.duration = None

            self.format = format
            self.channels = channels
            self.CHUNK = 1024
            self.pa_lib = pyaudio.PyAudio()
            self.device_name = device_name
            self.input_device_index = self.get_device_by_name(self.device_name)
            self.audio_sampling_rate = audio_sampling_rate

            self.name = "pyaudio '{}'".format(device_name)
            self.pa_stream = self.pa_lib.open(
                format=self.FORMAT_MAP[self.format],
                channels=self.channels,
                rate=self.audio_sampling_rate,
                input=True,
                frames_per_buffer=audio_sampling_rate * 10,
                input_device_index=self.input_device_index)
            self.pa_stream.start_stream()
            self.audioTime = int(time.time() * audio_sampling_rate)
            
        def update(self):
            #print("here")
            try:
                if self.pa_stream.get_read_available() == 0:
                    return (None, None)
                raw_data = self.pa_stream.read(self.pa_stream.get_read_available())
                unpacked_data = None
                if self.format == S16_LE:
                    unpacked_data = array(st_unpack(
                        "<%ih" % (len(raw_data)/2),
                        raw_data))
                elif self.format == S24_3LE:
                    unpacked_data = []
                    for i in range(int(len(raw_data)/3)):
                        chunk = raw_data[i*3:i*3+3]
                        unpacked_data.append(int.from_bytes(chunk, byteorder='little', signed=True))
                elif self.format == S32_LE:
                    unpacked_data = array(st_unpack(
                        "<%ii" % (len(raw_data)/4),
                        raw_data))
                
                self.audioTime += int(len(unpacked_data) / self.channels)
                unpacked_data = array(unpacked_data)
                return (unpacked_data.reshape(int(len(unpacked_data) / self.channels), self.channels), self.audioTime)
            except Exception as err:
                print("Error reading device", self.name)
                print(err)
                tb = traceback.extract_tb(err.__traceback__)
                print(tb)
                return(None, None)

        @staticmethod
        def query_input_devices():
            input_device_names = []
            for i in range(pyaudio.PyAudio().get_device_count()):
                device_info = pyaudio.PyAudio().get_device_info_by_index(i)
                # we are interrested only in input devices
                if device_info['maxInputChannels'] > 0:
                    hostapi_name = pyaudio.PyAudio() \
                        .get_host_api_info_by_index(
                            device_info['hostApi'])['name']
                    input_device_names.append(
                        "{}: {}"
                        .format(hostapi_name, device_info['name']))
            return input_device_names

        @staticmethod
        def get_device_by_name(device_name):
            if str == type(device_name):
                separator_pos = device_name.find(':')
                hostApi = pyaudio_soundcard.get_hostapi_by_name(
                    device_name[0:separator_pos])
                name = device_name[separator_pos+1:].strip()
                for i in range(pyaudio.PyAudio().get_device_count()):
                    device_info = pyaudio.PyAudio().get_device_info_by_index(i)
                    if ((device_info['hostApi'] == hostApi) and
                            (device_info['name'] == name)):
                        return i
            print(
                "Warning: pyaudio Device '{}' not found."
                .format(device_name))
            return None

        @staticmethod
        def get_hostapi_by_name(hostapi_name):
            for i in range(pyaudio.PyAudio().get_host_api_count()):
                host_api_info = pyaudio.PyAudio().get_host_api_info_by_index(i)
                if host_api_info['name'] == hostapi_name:
                    return host_api_info['index']
            print(
                "Warning: pyaudio Host API '{}' not found"
                .format(hostapi_name))
            return None

        def close(self):
            self.pa_stream.stop_stream()
            self.pa_stream.close()
            self.pa_lib.terminate()

        def info(self):
            print(self.name, "at", self.audio_sampling_rate, "Hz")
            try:
                one_sec = array([])
                tries = 0
                while tries < 20 and len(one_sec) < self.audio_sampling_rate:
                    (data, audio_time) = self.update()
                    if data is not None:
                        one_sec = numpy.append(one_sec, data)
                    tries += 1
                    time.sleep(0.1)
                if len(one_sec) < self.audio_sampling_rate:
                    print("The device generated no audio.")
                    return
                one_sec = one_sec[:self.audio_sampling_rate]
                one_sec = one_sec.reshape(self.audio_sampling_rate, self.channels)
                text_data = ""
                text_vector_sum = "Vector sum"
                peak_freq = []
                for channel in range(self.channels):
                    channel_one_sec = one_sec[:, channel]
                    peak_freq.append(get_peak_freq(
                        channel_one_sec,
                        self.audio_sampling_rate))
                    text_data += "[{} ... {}], ".format(
                        " ".join(str(i) for i in channel_one_sec[:5]),
                        " ".join(str(i) for i in channel_one_sec[-5:]))
                    text_vector_sum += " {},".format(channel_one_sec.sum())
                print(
                    "{:6d} "
                    "{} "
                    "read from {}, "
                    "shape {}, "
                    "format {}, "
                    "channel {}, "
                    "peak freq {} Hz"
                    .format(
                        len(channel_one_sec),
                        type(channel_one_sec[0]),
                        self.name,
                        one_sec.shape,
                        self.format,
                        channel,
                        peak_freq))
                print(text_data)
                print(text_vector_sum)
            except Exception as err:
                print("Exception", type(err), err)
                tb = traceback.extract_tb(err.__traceback__)
                print(tb)

except ImportError:
    pass


class GaplessSampler():
    """Sampler will gather sound capture from various devices."""

    def __init__(self, controller, audio_sampling_rate=96000, NFFT=None):
        self.version = "1.4 20160207"
        self.controller = controller
        self.scaling_factor = controller.config['scaling_factor']

        self.audio_sampling_rate = audio_sampling_rate
        if NFFT is not None:
            self.NFFT = NFFT
        else:
            # NFFT = 1024 for 44100 and 48000,
            #        2048 for 96000,
            #        4096 for 192000
            # -> the frequency resolution is constant
            self.NFFT = max(1024, 1024 * self.audio_sampling_rate // 48000)
        self.sampler_ok = True

        try:
            if controller.config['Audio'] == 'alsaaudio':
                self.capture_device = alsaaudio_soundcard(
                    controller.config['Card'],  # deprecated
                    controller.config['Device'],
                    audio_sampling_rate,
                    controller.config['Format'],
                    controller.config['Channels'],
                    controller.config['PeriodSize'])
            elif controller.config['Audio'] == 'sounddevice':
                self.capture_device = sounddevice_soundcard(
                    controller.config['Device'],
                    audio_sampling_rate,
                    controller.config['Format'],
                    controller.config['Channels'])
            elif controller.config['Audio'] == 'pyaudio':
                self.capture_device = pyaudio_soundcard(
                    controller.config['Device'],
                    audio_sampling_rate,
                    controller.config['Format'],
                    controller.config['Channels'])
            else:
                self.display_error_message(
                    "Unknown audio module:" + controller.config['Audio'])
                self.sampler_ok = False
        except Exception as err:
            self.sampler_ok = False
            self.display_error_message(
                "Could not open capture device. "
                "Please check your .cfg file or hardware.")
            print("Error", controller.config['Audio'])
            print(err)
            print(traceback.format_exc())

        if self.sampler_ok:
            print("-", self.capture_device.name)

    def set_monitored_frequencies(self, stations):
        self.monitored_channels = []
        self.monitored_bins = []
        for station in stations:
            self.monitored_channels.append(station['channel'])
            binSample = int(((int(station['frequency'])
                              * self.NFFT) / self.audio_sampling_rate))
            self.monitored_bins.append(binSample)
            # print ("monitored freq =", station[FREQUENCY],
            # " => bin = ", binSample)

    def update(self):
        try:
            return self.capture_device.update()
        except Exception as err:
            self.sampler_ok = False
            print(
                "Fail to read data from audio using "
                + self.capture_device.name)
            
            print(err)

    def close(self):
        if "capture_device" in dir(self):
            self.capture_device.close()

    def display_error_message(self, message):
        msg = "From Sampler object instance:\n" + message + ". Please check.\n"
        self.controller.viewer.status_display(msg)


def doTest(args, device, sampling_rate, format):
    if (args.device is None) or (args.device == device):
        if ((args.sampling_rate is None) or
                (args.sampling_rate == sampling_rate)):
            if (args.format is None) or (args.format == format):
                return True
    return False


if __name__ == '__main__':
    SAMPLING_RATES = [44100, 48000, 96000, 192000]
    FORMATS = [S16_LE, S24_3LE, S32_LE]
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-l", "--list",
        help="list the potential module and device combinations and exit",
        action='store_true')
    parser.add_argument(
        "-m", "--module",
        help="audio module",
        choices=audioModule,
        default=None)
    parser.add_argument(
        "-d", "--device",
        help="fully qualified device name",
        default=None)
    parser.add_argument(
        "-s", "--sampling-rate",
        help="sampling rate",
        choices=SAMPLING_RATES,
        type=int,
        default=None)
    parser.add_argument(
        "-f", "--format",
        help="format to be captured",
        choices=FORMATS,
        default=None)
    parser.add_argument(
        "-p", "--periodsize",
        help="""periodsize parameter of the PCM interface
default=1024, if the computer runs out of memory,
select smaller numbers like 128, 256, 512, ...""",
        type=int,
        default=1024)
    parser.add_argument(
        "-n", "--channels",
        help="number of channels, default=1",
        choices=[1, 2],
        type=int,
        default=1)
    args = parser.parse_args()

    # -l/--list is an exclusive parameter, exit after execution
    if args.list:
        if 'alsaaudio' in audioModule:
            devices = alsaaudio.pcms()
            for device in devices:
                print('--module=alsaaudio --device="{}"'.format(device))
            print()
        if 'sounddevice' in audioModule:
            devices = sounddevice_soundcard.query_input_devices()
            for device in devices:
                print('--module=sounddevice --device="{}"'.format(device))
            print()
        if 'pyaudio' in audioModule:
            devices = pyaudio_soundcard.query_input_devices()
            for device in devices:
                print('--module=pyaudio --device="{}"'.format(device))
            print()
        sys.exit(0)

    if (args.module is None) or (args.module == 'alsaaudio'):
        if 'alsaaudio' in audioModule:
            devices = alsaaudio.pcms()
            for device in devices:
                for sampling_rate in SAMPLING_RATES:
                    for format in FORMATS:
                        if doTest(args, device, sampling_rate, format):
                            alsaaudio_test(
                                device,
                                sampling_rate,
                                format,
                                args.channels,
                                args.periodsize)
        else:
            print("not installed.")

    if (args.module is None) or (args.module == 'sounddevice'):
        if 'sounddevice' in audioModule:
            devices = sounddevice_soundcard.query_input_devices()
            for device in devices:
                for sampling_rate in SAMPLING_RATES:
                    for format in FORMATS:
                        if doTest(args, device, sampling_rate, format):
                            sounddevice_test(
                                device,
                                sampling_rate,
                                format,
                                args.channels)
        else:
            print("not installed.")

    if (args.module is None) or (args.module == 'pyaudio'):
        if 'pyaudio' in audioModule:
            devices = pyaudio_soundcard.query_input_devices()
            for device in devices:
                for sampling_rate in SAMPLING_RATES:
                    for format in FORMATS:
                        if doTest(args, device, sampling_rate, format):
                            pyaudio_test(
                                device,
                                sampling_rate,
                                format,
                                args.channels)
        else:
            print("not installed.")
