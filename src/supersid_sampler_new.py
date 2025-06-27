"""
Define 2 abstract base classes that define the common interface for:
1) AudioAPI represents an audio api (ie sounddevice, pyaudio, pyalsaaudio, etc)
2) AudioInputDevice represents a device that can be used to capture audio

Currently this file contains implementations of the concrete classes
which implement these, but they will later be split out into separate files
that do not need to be present when not required
"""

import time
from numpy import array
from matplotlib.mlab import psd as mlab_psd

from supersid_config import FREQUENCY, S16_LE, S24_3LE, S32_LE

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

class AudioAPI:
    """Abstract base class for the AudioAPI."""

    api_list = []
    @classmethod
    def get_apis(cls):
        """Return a list of available AudioAPI instances."""
        return cls.api_list

    def __init__(self, api_name):
        self.api_name = api_name
        self.device_list = []
        self.api_list.append(self)

    def get_api_name(self):
        return self.api_name

    def get_device_list(self):
        return self.device_list

    def build_device_list(self):
        """
            Populates the self.device_list attribute with a list of AudioInputDevice objects.

            All concrete classes must implement this method.
        """
        raise NotImplementedError

    def show_all_devices(self):
        for device in self.device_list:
            device_info = device.get_device_info()
            print(device_info)

class AudioInputDevice():
    """Abstract base class for the AudioInputDevice."""
    def __init__(self, device_info, apiobj):
        self.apiobj = apiobj
        self.device_info = device_info

    def get_device_info(self):
        """returns a dictionary with device info."""
        return self.device_info

    def capture_data(self, duration):
        """Capture duration seconds of audio data."""
        raise NotImplementedError

    def test_audio_device(self, sampling_rate, format, channels):
        print(f"Test {self.device_info['name']} sampling rate {sampling_rate}",
              f"format {format} channels {channels}")
        self.sampling_rate = sampling_rate
        self.format = format
        self.channels = channels
        try:
            one_sec = self.capture_data(1.0)

            text_data = ""
            text_vector_sum = "Vector sum"
            peak_freq = []
            for channel in range(self.channels):
                channel_one_sec = one_sec[:, channel]
                peak_freq.append(get_peak_freq(channel_one_sec, self.audio_sampling_rate))
                text_data += "[{} ... {}], ".format(" ".join(str(i) for i in channel_one_sec[:5]),
                    " ".join(str(i) for i in channel_one_sec[-5:]))
                text_vector_sum += f" {channel_one_sec.sum()},"
            print(f"Size {len(channel_one_sec):6d} ",
                  f"dtype {type(channel_one_sec[0])} ",
                  f"read from {self.device_info['name']}, ",
                  f"shape {one_sec.shape}, ",
                  f"format {self.format}, ",
                  f"channel {channel}, ",
                  f"duration {self.actual_duration:3.2f} sec, ",
                  f"peak freq {peak_freq} Hz")
            print(text_data)
            print(text_vector_sum)
        except NotImplementedError as e:
            print(e)

"""This should go in a separate module """
import sounddevice as sd

class SounddeviceAPI(AudioAPI):
    """Concrete implementation of the SounddeviceAPI."""
    def __init__(self):
        super().__init__("sounddevice")

    def build_device_list(self):
        for device_info in sd.query_devices():
            if device_info['max_input_channels'] > 0:
                device_obj = SounddeviceInputDevice(device_info, self)
                self.device_list.append(device_obj)

    def get_device_list(self):
        return self.device_list



class SounddeviceInputDevice(AudioInputDevice):
    # map ALSA format string to module format
    FORMAT_MAP = {# Signed 16 bit samples stored in 2 bytes, Little Endian byte order
        S16_LE: 'int16',

        # Signed 24 bit samples stored in 3 bytes, Little Endian byte order
        S24_3LE: 'int24',

        # Signed 32 bit samples stored in 4 bytes, Little Endian byte order
        S32_LE: 'int32', }

    def get_input_channels(self):
        return self.device_info['max_input_channels']

    def __init__(self, device_info, apiobj):
        super().__init__(device_info['name'], apiobj)
        self.device_info = device_info
        self.audio_sampling_rate = int(device_info['default_samplerate'])
        self.channels = device_info['max_input_channels']

    def capture_data(self, requested_duration=1.0):
        """
        return one second recording as numpy array
        after unpacking, the format is
            for Channels = 1: [left, ..., left]
            for Channels = 2: [left, right ..., left, right]

        the returned data format is
            for Channels = 1: [[left], ..., [left]]
            for Channels = 2: [[left, right], ..., [left, right]]

        access the left channel as unpacked_data[:, 0]
        access the right channel as unpacked_data[:, 1]
        """
        unpacked_data = array([])
        try:
            t = time.time()
            if self.format in [S16_LE, S32_LE]:
                unpacked_data = sd.rec(
                    frames=int(self.audio_sampling_rate * requested_duration),
                    dtype=self.FORMAT_MAP[self.format],
                    channels=self.channels,
                    blocking=True).flatten()
            else:
                # 'int24' is not supported by sounddevice.rec(),
                # instead sounddevice.RawInputStream() has to be used
                # in combination with a callback to consume the data
                raise NotImplementedError(
                    "'int24' is not supported by sounddevice.rec()")
            self.actual_duration = time.time() - t
            assert (len(unpacked_data) ==
                    (self.audio_sampling_rate * self.channels * requested_duration)), \
                "expected the number of samples to be identical with " \
                "sampling rate * number of channels"
        except sd.PortAudioError as err:
            print("Error reading device", self.name)
            print(err)
        return unpacked_data.reshape((
            self.audio_sampling_rate,
            self.channels))

"""This should go in a separate module """
import pyaudio
class PyaudioAPI(AudioAPI):
    """Concrete implementation of the SounddeviceAPI."""
    def __init__(self):
        super().__init__("pyaudio")

    def build_device_list(self):
        for i in range(pyaudio.PyAudio().get_device_count()):
            device_info = pyaudio.PyAudio().get_device_info_by_index(i)
            if device_info['maxInputChannels'] > 0:
                device_obj = PyaudioInputDevice(device_info, self)
                self.device_list.append(device_obj)

class PyaudioInputDevice(AudioInputDevice):
    # map ALSAO format string to length of one sample in bytes
    FORMAT_LENGTHS = {S16_LE: 2, S24_3LE: 3, S32_LE: 4}
    # map ALSA format string to module format
    FORMAT_MAP = {# Signed 16 bit samples stored in 2 bytes, Little Endian byte order
        S16_LE: pyaudio.paInt16,

        # Signed 24 bit samples stored in 3 bytes, Little Endian byte order
        S24_3LE: pyaudio.paInt24,

        # Signed 32 bit samples stored in 4 bytes, Little Endian byte order
        S32_LE: pyaudio.paInt32
    }

    def __init__(self, device_info, apiobj):
        super().__init__(device_info['name'], apiobj)
        self.device_info = device_info
        self.audio_sampling_rate = int(device_info['defaultSampleRate'])
        self.channels = device_info['maxInputChannels']
        self.CHUNK = 1024

        self.pa_lib = pyaudio.PyAudio()
        self.open_stream()

    def open_stream(self):
        self.pa_stream = self.pa_lib.open(format=self.FORMAT_MAP[self.format],
                                          channels=self.channels,
                                          rate=self.audio_sampling_rate,
                                          input=True,
                                          frames_per_buffer=self.CHUNK,
                                          input_device_index=self.input_device_index)

    def get_input_channels(self):
        return self.device_info['maxInputChannels']

    def capture_data(self, duration):
        """
        return one second recording as numpy array
        after unpacking, the format is
            for Channels = 1: [left, ..., left]
            for Channels = 2: [left, right ..., left, right]

        the returned data format is
            for Channels = 1: [[left], ..., [left]]
            for Channels = 2: [[left, right], ..., [left, right]]

        access the left channel as unpacked_data[:, 0]
        access the right channel as unpacked_data[:, 1]
        """
        self.pa_stream = self.pa_lib.open(format=self.FORMAT_MAP[self.format],
                                          channels=self.channels,
                                          rate=self.audio_sampling_rate,
                                          input=True,
                                          frames_per_buffer=self.CHUNK,
                                          input_device_index=self.input_device_index)

        raw_data = b''
        num_bytes = self.FORMAT_LENGTHS[self.format] * self.channels * self.audio_sampling_rate
        t = time.time()
        while len(raw_data) < num_bytes:
            length, data = self.inp.read()
            if length > 0:
                raw_data += data
        self.duration = time.time() - t

        # truncate to one second, if we received too much
        raw_data = raw_data[:num_bytes]

        if self.format == S16_LE:
            unpacked_data = array(
                st_unpack("<%ih" % (self.audio_sampling_rate * self.channels), raw_data))
            return unpacked_data.reshape((self.audio_sampling_rate, self.channels))
        elif self.format == S24_3LE:
            unpacked_data = []
            for i in range(self.audio_sampling_rate * self.channels):
                chunk = raw_data[i * 3:i * 3 + 3]
                unpacked_data.append(
                    st_unpack('<i', chunk + (b'\0' if chunk[2] < 128 else b'\xff'))[0])
            return array(unpacked_data).reshape((self.audio_sampling_rate, self.channels))
        elif self.format == S32_LE:
            unpacked_data = array(
                st_unpack("<%ii" % (self.audio_sampling_rate * self.channels), raw_data))
            return unpacked_data.reshape((self.audio_sampling_rate, self.channels))
        else:
            raise NotImplementedError(
                f"Format conversion for '{self.format}' is not yet implemented!")

    def close_stream(self):
        """Close audio stream if we need to change parameters"""
        self.pa_stream.stop_stream()
        self.pa_stream.close()

    def close(self):
        self.pa_lib.terminate()


"""Testing code and example"""
def main():

    SAMPLING_RATES = [44100, 48000, 96000, 192000]
    FORMATS = [S16_LE, S24_3LE, S32_LE]

    try:
        import sounddevice
        sound_api = SounddeviceAPI()
    except ImportError:
        print("sounddevice not installed")

    try:
        import pyaudio
        pyaudio_api = PyaudioAPI()
    except ImportError:
        print("pyaudio not installed")

    for api in AudioAPI.get_apis():
        print(f"-----{api.api_name}-----")
        api.build_device_list()
        api.show_all_devices()
        if api.get_api_name() == "pyaudio":
            dev_list = api.get_device_list()
            for dev in dev_list:
                for data_format in FORMATS:
                    for sample_rate in SAMPLING_RATES:
                        dev.test_audio_device(sample_rate, data_format, dev.get_input_channels())

if __name__ == '__main__':
    main()
