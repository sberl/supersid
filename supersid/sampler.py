#!/usr/bin/env python3
"""
Sampler handles audio data capture.

Also handles calculating PSD, extracting signal strengths at monitored
frequencies, saving spectrum and spectrogram (image) to png file

This is pure Model, no wx import possible else Thread conflict

The Sampler class will use an audio 'device' to capture 1 second of sound.
This 'device' can be a local sound card:
     - controlled by pyaudio on Windows or other system
     - controlled by alsaaudio on Linux
    or this 'device' can be a remote server
     - client mode accessing server thru TCP/IP socket (to be implemented)

    All these 'devices' must implement:
     - __init__: open the 'device' for future capture
     - capture_1sec: obtain one second of sound and return as an array
        of 'audio_sampling_rate' integers
     - close: close the 'device'
"""
# 20150801:
#   - modify the __main__ to help debugging the soundcard
from struct import unpack as st_unpack
from numpy import array
import time

from config import DEVICE_DEFAULT, FREQUENCY # get value from config.py

audioModule = []
try:
    import alsaaudio  # for Linux direct sound capture
    audioModule.append("alsaaudio")
    # pip3 install setuptools
    # dnf install python3-cffi
    # dnf install portaudio
    # pip3 install sounddevice

    class alsaaudio_soundcard():
        """Sampler for an ALSA audio device."""

        def __init__(self, card, device, periodsize, audio_sampling_rate):
            """Initialize the ALSA audio sampler."""
            self.FORMAT = alsaaudio.PCM_FORMAT_S16_LE   # Signed 16 bit samples for each channel Little Endian byte order)
            self.audio_sampling_rate = audio_sampling_rate
            if device != DEVICE_DEFAULT:
                print("alsaaudio using device:", device)
                self.inp = alsaaudio.PCM(alsaaudio.PCM_CAPTURE,
                                         alsaaudio.PCM_NORMAL,
                                         channels=1,
                                         rate=audio_sampling_rate,
                                         format=self.FORMAT,
                                         periodsize=periodsize,
                                         device=device)
                self.name = "alsaaudio '{}'".format(device)
            else:
                card = 'sysdefault:CARD=' + card  # .cfg file under [Capture] section
                print("alsaaudio using card", card)
                self.inp = alsaaudio.PCM(alsaaudio.PCM_CAPTURE,
                                         alsaaudio.PCM_NORMAL,
                                         channels=1,
                                         rate=audio_sampling_rate,
                                         format=self.FORMAT,
                                         periodsize=periodsize,
                                         device=card)
                self.name = "alsaaudio '{}'".format(card)

        def capture_1sec(self):
            raw_data = b''
            while len(raw_data) < 2 * self.audio_sampling_rate:
                length, data = self.inp.read()
                if length > 0:
                    raw_data += data
            return array(st_unpack("%ih" % self.audio_sampling_rate,
                                   raw_data[:2 * self.audio_sampling_rate]))

        def close(self):
            pass  # to check later if there is something to do

        def info(self):
            print(self.name, "at", self.audio_sampling_rate, "Hz")
            try:
                t = time.time()
                one_sec = self.capture_1sec()
                print("{:6d} {} read from {}, shape {}, duration {:3.2f}".format(len(one_sec), type(one_sec[0]), self.name, one_sec.shape, time.time() - t))
                print(one_sec[:10])
                print("Vector sum", one_sec.sum())
            except IndexError:
                print("Cannot read", self.name)

except ImportError:
    pass


try:
    import sounddevice  # for Linux and Windows http://python-sounddevice.readthedocs.org
    audioModule.append("sounddevice")

    class sounddevice_soundcard():
        @staticmethod
        def query_input_devices():
            input_device_names = []
            for device_info in sounddevice.query_devices():
                if device_info['max_input_channels'] > 0:     # we are interrested only in input devices
                    hostapi_name = sounddevice.query_hostapis(device_info['hostapi'])['name']
                    input_device_names.append("{}: {}".format(hostapi_name, device_info['name']))
            return input_device_names

        @staticmethod
        def get_device_by_name(device_name):
            if str == type(device_name):
                separator_pos = device_name.find(':')
                hostapi = sounddevice_soundcard.get_hostapi_by_name(device_name[0:separator_pos])
                name = device_name[separator_pos+1:].strip()
                for i, device_info in enumerate(sounddevice.query_devices()):
                    if (device_info['hostapi'] == hostapi) and (device_info['name'] == name):
                        return i
            print("Warning: '{}' not found".format(device_name))
            return None

        @staticmethod
        def get_hostapi_by_name(hostapi_name):
            hostapis = sounddevice.query_hostapis()
            for index, host_api_info in enumerate(hostapis):
                if host_api_info['name'] == hostapi_name:
                    return index
            print("Warning: '{}' not found".format(hostapi_name))
            return None

        def __init__(self, device_name, audio_sampling_rate):
            self.audio_sampling_rate = audio_sampling_rate
            self.device_name = device_name
            sounddevice.default.samplerate = audio_sampling_rate
            sounddevice.default.device = self.get_device_by_name(self.device_name)
            sounddevice.default.channels = 1
            sounddevice.default.latency = 'low'
            sounddevice.default.dtype = 'int16'
            self.name = "sounddevice '{}'".format(self.device_name)

        def capture_1sec(self):
            # duration = 1 sec hence
            # 1 x self.audio_sampling_rate = self.audio_sampling_rate
            one_sec_record = b''
            try:
                one_sec_record = sounddevice.rec(frames=self.audio_sampling_rate, blocking=True).flatten()
                assert(len(one_sec_record) == self.audio_sampling_rate)
            except sounddevice.PortAudioError as err:
                print("Error reading device", self.name)
                print(err)
            return one_sec_record

        def close(self):
            pass  # to check later if there is something to do

        def info(self):
            print(self.name, "at", self.audio_sampling_rate, "Hz")
            assert(sounddevice.default.device[0] == self.get_device_by_name(self.device_name))  # index 0 of sounddevice.default.device is the input device
            try:
                t = time.time()
                one_sec = self.capture_1sec()
                print("{:6d} {} read from {}, shape {}, duration {:3.2f}".format(len(one_sec), type(one_sec[0]), self.name, one_sec.shape, time.time() - t))
                print(one_sec[:10])
                print("Vector sum", one_sec.sum())
            except IndexError:
                print("Cannot read", self.name)

except ImportError:
    pass


try:
    import pyaudio  # for Linux with jackd OR windows
    audioModule.append("pyaudio")

    class pyaudio_soundcard():
        @staticmethod
        def query_input_devices():
            input_device_names = []
            for i in range(pyaudio.PyAudio().get_device_count()):
                device_info = pyaudio.PyAudio().get_device_info_by_index(i)
                if device_info['maxInputChannels'] > 0:     # we are interrested only in input devices
                    hostapi_name = pyaudio.PyAudio().get_host_api_info_by_index(device_info['hostApi'])['name']
                    input_device_names.append("{}: {}".format(hostapi_name, device_info['name']))
            return input_device_names

        @staticmethod
        def get_device_by_name(device_name):
            if str == type(device_name):
                separator_pos = device_name.find(':')
                hostApi = pyaudio_soundcard.get_hostapi_by_name(device_name[0:separator_pos])
                name = device_name[separator_pos+1:].strip()
                for i in range(pyaudio.PyAudio().get_device_count()):
                    device_info = pyaudio.PyAudio().get_device_info_by_index(i)
                    if (device_info['hostApi'] == hostApi) and (device_info['name'] == name):
                        return i
            print("Warning: '{}' not found.".format(device_name))
            return None

        @staticmethod
        def get_hostapi_by_name(hostapi_name):
            for i in range(pyaudio.PyAudio().get_host_api_count()):
                host_api_info = pyaudio.PyAudio().get_host_api_info_by_index(i)
                if host_api_info['name'] == hostapi_name:
                    return host_api_info['index']
            print("Warning: '{}' not found".format(hostapi_name))
            return None

        def __init__(self, device_name, audio_sampling_rate):
            self.FORMAT = pyaudio.paInt16
            self.CHUNK = 1024
            self.pa_lib = pyaudio.PyAudio()
            self.device_name = device_name
            self.input_device_index = self.get_device_by_name(self.device_name)
            self.audio_sampling_rate = audio_sampling_rate

            self.pa_stream = self.pa_lib.open(format=self.FORMAT,
                                              channels=1,
                                              rate=self.audio_sampling_rate,
                                              input=True,
                                              frames_per_buffer=self.CHUNK,
                                              input_device_index=self.input_device_index)
            self.name = "pyaudio '{}'".format(device_name)

        def capture_1sec(self):
            raw_data = bytearray(self.capture(1))
            unpacked_data = st_unpack("{}h".format(self.audio_sampling_rate),
                                      raw_data)
            return array(unpacked_data)

        def capture(self, secs):
            frames = []
            # int(self.audio_sampling_rate / self.CHUNK * secs)
            expected_number_of_bytes = 2 * self.audio_sampling_rate * secs
            while len(frames) < expected_number_of_bytes:
                try:
                    data = self.pa_stream.read(self.CHUNK, exception_on_overflow=False)
                    frames.extend(data)
                    # print(len(data), len(frames))
                except IOError as err:
                    print("IOError reading card:", str(err))
                    if -9981 == err.errno: # input overflow:
                        # this should not happen with exception_on_overflow=False
                        pass
                    else:
                        break   # avoid an endless loop, i.e. with error -9988
            return frames[:expected_number_of_bytes]

        def close(self):
            self.pa_stream.stop_stream()
            self.pa_stream.close()
            self.pa_lib.terminate()

        def info(self):
            print(self.name, "at", self.audio_sampling_rate, "Hz")
            try:
                t = time.time()
                one_sec = self.capture_1sec()
                print("{:6d} {} read from {}, shape {}, duration {:3.2f}".format(len(one_sec), type(one_sec[0]), self.name, one_sec.shape, time.time() - t))
                print(one_sec[:10])
                print("Vector sum", one_sec.sum())
            except IndexError:
                print("Cannot read", self.name)

except ImportError:
    pass


class Sampler():
    """Sampler will gather sound capture from various devices."""

    def __init__(self, controller, audio_sampling_rate=96000, NFFT=1024):
        self.version = "1.4 20160207"
        self.controller = controller
        self.scaling_factor = controller.config['scaling_factor']

        self.audio_sampling_rate = audio_sampling_rate
        self.NFFT = NFFT
        self.sampler_ok = True

        try:
            if controller.config['Audio'] == 'pyaudio':
                self.capture_device = pyaudio_soundcard(
                    controller.config['Card'], audio_sampling_rate)
            elif controller.config['Audio'] == 'sounddevice':
                self.capture_device = sounddevice_soundcard(
                    controller.config['Card'], audio_sampling_rate)
            elif controller.config['Audio'] == 'alsaaudio':
                self.capture_device = alsaaudio_soundcard(
                    controller.config['Card'],
                    controller.config['Device'],
                    controller.config['PeriodSize'],
                    audio_sampling_rate)
            else:
                self.display_error_message(
                    "Unknown audio module:" + controller.config['Audio'])
                self.sampler_ok = False
        except Exception as err:
            self.sampler_ok = False
            self.display_error_message("Could not open capture device. Please check your .cfg file or hardware.")
            print ("Error", controller.config['Audio'])
            print(err)
            print("To debugg: remove the try/except clause to get detail on what exception is triggered.")

        if self.sampler_ok:
            print("-", self.capture_device.name)

    def set_monitored_frequencies(self, stations):
        self.monitored_bins = []
        for station in stations:
            binSample = int(((int(station['frequency'])
                              * self.NFFT) / self.audio_sampling_rate))
            self.monitored_bins.append(binSample)
            # print ("monitored freq =", station[FREQUENCY],
            # " => bin = ", binSample)

    def capture_1sec(self):
        """Capture 1 second of data, returned data as an array
        """
        try:
            self.data = self.capture_device.capture_1sec()
        except:
            self.sampler_ok = False
            print ("Fail to read data from audio using "
                   + self.capture_device.name)
            self.data = []
        else:
            # Scale A/D raw_data to voltage here
            # Might substract 5v to make the data look more like SID
            if(self.scaling_factor != 1.0):
                self.data *= self.scaling_factor

        return self.data

    def close(self):
        self.capture_device.close()

    def display_error_message(self, message):
        msg = "From Sampler object instance:\n" + message + ". Please check.\n"
        self.controller.viewer.status_display(msg)


if __name__ == '__main__':

    print('Possible capture modules:', audioModule)
    print("\nalsaaudio:")

    if 'alsaaudio' in audioModule:
        cards = alsaaudio.cards()
        print("\n".join(cards))
        for card in cards:
            for sampling_rate in [48000, 96000, 192000]:
                print()
                try:
                    print("Accessing '{}' at {} Hz via alsaaudio, ...".format(card, sampling_rate))
                    sc = alsaaudio_soundcard(card, DEVICE_DEFAULT, 1024, sampling_rate)
                    sc.info()
                except alsaaudio.ALSAAudioError as err:
                    print("! ERROR capturing sound on card '{}'".format(card))
                    print(err)
    else:
        print("not installed.")

    print("\n", "- "*60)
    print("sounddevice:")

    if 'sounddevice' in audioModule:
        devices = sounddevice_soundcard.query_input_devices()
        print("\n".join(devices))
        for device_name in devices:
            for sampling_rate in [48000, 96000, 192000]:
                print()
                try:
                    print("Accessing '{}' at {} Hz via sounddevice, ...".format(device_name, sampling_rate))
                    sc = sounddevice_soundcard(device_name, sampling_rate)
                    sc.info()
                except Exception as err:
                    print("! ERROR capturing sound on card '{}'".format(device_name))
                    print(err)
    else:
        print("not installed.")

    print("\n", "- "*60)
    print("pyaudio:")

    if 'pyaudio' in audioModule:
        devices = pyaudio_soundcard.query_input_devices()
        print("\n".join(devices))
        for device_name in devices:
            for sampling_rate in [48000, 96000, 192000]:
                print()
                try:
                    print("Accessing '{}' at {} Hz via pyaudio, ...".format(device_name, sampling_rate))
                    sc = pyaudio_soundcard(device_name, sampling_rate)
                    sc.info()
                except Exception as err:
                    print("! ERROR capturing sound on card '{}'".format(device_name))
                    print(err)
    else:
        print("not installed.")
