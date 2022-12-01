#!/usr/bin/env python3

import os
import sys
import re
import glob
import time
import wave
import struct
import shutil
import subprocess
import argparse
from argparse import RawTextHelpFormatter
import pkg_resources    # python3 -m pip install setuptools
from struct import unpack as st_unpack
from numpy import array
from matplotlib.mlab import psd as mlab_psd
from pprint import pprint
import pandas as pd     # python3 -m pip install pandas
import numpy as np

from config import readConfig, CONFIG_FILE_NAME
from supersid_common import exist_file, slugify
from isine import SinePlayer


if __name__ == '__main__':
    print("Version 20220105")


"""
1)  query capabilities of capture devices from 'arecord'
2a) generate a test tone which should be looped back
    with an audio cable from line out to line in
2b) walk through alsaaudio pcms and test with the capabilities
    of the capture devices known from 'arecord'
"""

DEFAULT_RATES = [44100, 48000, 96000, 192000]
DEFAULT_FORMATS = ['S16_LE', 'S24_3LE', 'S32_LE']

# actually we don't know but let's assume there is at least one channel
DEFAULT_CHANNELS = 1

BAD_DEVICES = [
    'upmix',       # Segmenation fault (core dumped)
    'vdownmix',    # Segmenation fault (core dumped)
    ]


class alsa(object):
    # https://github.com/torvalds/linux/blob/master/include/sound/pcm.h
    # SNDRV_PCM_RATE_*, values in Hz
    sndrv_pcm_rates = [
        5512, 8000, 11025, 16000, 22050, 32000, 44100, 48000, 64000, 88200,
        96000, 176400, 192000, 352800, 384000]

    # https://vovkos.github.io/doxyrest/samples/alsa-sphinxdoc/enum_snd_pcm_access_t.html
    snd_pcm_access_t = {
        'MMAP_INTERLEAVED ': 0,
        'MMAP_NONINTERLEAVED': 1,
        'MMAP_COMPLEX': 2,
        'RW_INTERLEAVED': 3,
        'RW_NONINTERLEAVED': 4,
        'LAST': 4,  # RW_NONINTERLEAVED
    }

    # https://vovkos.github.io/doxyrest/samples/alsa-sphinxdoc/enum_snd_pcm_format_t.html
    snd_pcm_format_t = {
        'UNKNOWN': -1,
        'S8': 0,
        'U8': 1,
        'S16_LE': 2,
        'S16_BE': 3,
        'U16_LE': 4,
        'U16_BE': 5,
        'S24_LE': 6,
        'S24_BE': 7,
        'U24_LE': 8,
        'U24_BE': 9,
        'S32_LE': 10,
        'S32_BE': 11,
        'U32_LE': 12,
        'U32_BE': 13,
        'FLOAT_LE': 14,
        'FLOAT_BE': 15,
        'FLOAT64_LE': 16,
        'FLOAT64_BE': 17,
        'IEC958_SUBFRAME_LE': 18,
        'IEC958_SUBFRAME_BE': 19,
        'MU_LAW': 20,
        'A_LAW': 21,
        'IMA_ADPCM': 22,
        'MPEG': 23,
        'GSM': 24,
        'SPECIAL': 31,
        'S24_3LE': 32,
        'S24_3BE': 33,
        'U24_3LE': 34,
        'U24_3BE': 35,
        'S20_3LE': 36,
        'S20_3BE': 37,
        'U20_3LE': 38,
        'U20_3BE': 39,
        'S18_3LE': 40,
        'S18_3BE': 41,
        'U18_3LE': 42,
        'U18_3BE': 43,
        'G723_24': 44,
        'G723_24_1B': 45,
        'G723_40': 46,
        'G723_40_1B': 47,
        'DSD_U8': 48,
        'DSD_U16_LE': 49,
        'DSD_U32_LE': 50,
        'DSD_U16_BE': 51,
        'DSD_U32_BE': 52,
        'LAST': 52,  # DSD_U32_BE
        'S16': 2,  # S16_LE
        'U16': 4,  # U16_LE
        'S24': 6,  # S24_LE
        'U24': 8,  # U24_LE
        'S32': 10,  # S32_LE
        'U32': 12,   # U32_LE
        'FLOAT': 14,  # FLOAT_LE
        'FLOAT64': 16,  # FLOAT64_LE
        'IEC958_SUBFRAME': 18,  # IEC958_SUBFRAME_LE
    }

    # https://vovkos.github.io/doxyrest/samples/alsa-sphinxdoc/enum_snd_pcm_subformat_t.html
    snd_pcm_subformat_t = {
        'STD': 0,
        'LAST': 0,  # STD
    }

    def __new__(cls, executable_name, verbose):
        executable = shutil.which(executable_name)
        if executable is None:
            print(
                "ERROR: '{}' executable could not be found!"
                .format(executable_name))
            return None
        else:
            instance = super(alsa, cls).__new__(cls)
            instance.executable = executable
            instance.verbose = verbose
            return instance

    def __init__(self, verbose):
        self.process = None
        self.verbose = verbose

    def start(self, args):
        if self.process is None:
            if self.verbose:
                print(" ".join(s for s in [self.executable] + args))
            self.process = subprocess.Popen(
                [self.executable] + args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)

    def kill(self):
        if self.process is not None:
            self.process.kill()
            self.process = None

    def exec(self, args, return_error=False):
        if self.process is not None:
            print("ERROR: a process is already running")
        self.start(args)
        stdout, stderr = self.process.communicate()
        errorlevel = self.process.returncode
        self.process = None
        stdout = stdout.decode()
        stderr = stderr.decode()
        if return_error:
            return stdout, stderr, errorlevel
        else:
            if errorlevel:
                print(
                    "ERROR: '{}' returned errorlevel {}"
                    .format(" ".join(args), errorlevel))
                sys.exit(errorlevel)
            elif stderr:
                print(
                    "ERROR: '{}' returned stderr '{}'"
                    .format(" ".join(args), stderr))
                sys.exit(1)
            else:
                return stdout

    def get_pcms(self):
        """arecord -L, --list-pcms         list device names"""
        """aplay -L, --list-pcms         list device names"""
        pcms = []
        stdout = self.exec(['--list-pcms'])
        stdout = stdout.split('\n')
        for line in stdout:
            m = re.match('.*:CARD=.*', line)
            if m:
                pcms.append(line)
        return pcms


class aplay(alsa):
    def __new__(cls, verbose):
        return alsa.__new__(cls, 'aplay', verbose)


class speaker_test():
    def __new__(cls, verbose):
        ap = aplay(verbose)
        if ap is None:
            return None
        else:
            instance = super(speaker_test, cls).__new__(cls)
            instance.ap = ap
            instance.verbose = verbose
            instance.isine = None
            return instance

    def get_pcms(self):
        return self.ap.get_pcms()

    def start_test_tone(self, card, rate, frequency=10000):
        """assumption: plughw: will generate the test tone"""
        if "CARD=" == card[0:5]:
            # by experience the 'plughw:CARD=xxxx' are working best
            device = "plughw:{}".format(card)
        else:
            device = card
        if self.isine is None:
            pcms = self.get_pcms()
            found = False
            if device in pcms:
                found = True            # full match
            else:
                if ',DEV=' in device:
                    device = device[:device.find(',DEV=')]
                for pcm in pcms:
                    if device in pcm:
                        device = pcm
                        found = True    # partial match
                        break
            if found:
                try:
                    self.isine = SinePlayer(device, rate, frequency)
                    self.isine.start()
                    time.sleep(2.0)
                    print(
                        "test tone started {} Hz, '{}'"
                        .format(int(self.isine.frequency), device))
                except Exception as e:
                    print("ERROR:", type(e), e)
            else:
                print(
                    "ERROR: device '{}' not found for test tone generation"
                    .format(device))
        else:
            print("usage error: test tone is already active")

    def stop_test_tone(self):
        if self.isine:
            self.isine.stop()
            del(self.isine)
            self.isine = None
            print("test tone stopped")


class arecord(alsa):
    def __new__(cls, verbose):
        return alsa.__new__(cls, 'arecord', verbose)

    def parse_hw_params(self, text):
        """
        sample outpout of arecord --dump-hw-params
        the part between the dashed lines is the relevant on

            Recording WAVE 'stdin' : Signed 16 bit Little Endian, Rate 8000 Hz, Mono
            HW Params of device "hw:CARD=Generic,DEV=0":
            --------------------
            ACCESS:  MMAP_INTERLEAVED RW_INTERLEAVED
            FORMAT:  S16_LE S32_LE
            SUBFORMAT:  STD
            SAMPLE_BITS: [16 32]
            FRAME_BITS: [32 64]
            CHANNELS: 2
            RATE: [44100 192000]
            PERIOD_TIME: (83 185760)
            PERIOD_SIZE: [16 8192]
            PERIOD_BYTES: [128 65536]
            PERIODS: [2 32]
            BUFFER_TIME: (166 371520)
            BUFFER_SIZE: [32 16384]
            BUFFER_BYTES: [128 65536]
            TICK_TIME: ALL
            --------------------
            arecord: set_params:1374: Channels count non available

        the above output is generated from
            https://github.com/michaelwu/alsa-lib/blob/master/src/pcm/pcm.c
                snd_pcm_hw_params_dump()
                -> dump_one_param() -> snd_pcm_hw_param_dump()
            https://github.com/michaelwu/salsa-lib/blob/master/src/pcm_params.c
                snd_pcm_hw_param_dump()
                -> snd_mask_print() | snd_interval_print()
        data layout:
            key: values
            snd_mask_print()
                mask_is_empty -> 'NONE'
                mask_is_full  -> 'ALL'
                else:
                    for each bit in ACCESS:
                        ACCESS string snd_pcm_access_name(i),
                        see snd_pcm_access_t
                    for each bit in FORMAT:
                        FORMAT string snd_pcm_format_name(i),
                        see snd_pcm_format_t
                    for each bit in SUBFORMAT:
                        SUBFORMAT string snd_pcm_subformat_name(),
                        see snd_pcm_subformat_t
            snd_interval_print()
                interval_is_empty -> 'NONE'
                interval_is_full -> 'ALL'
                interval_is_single -> integer
                else:
                    (min max) | [min max] | (min max] | [min max)
                    '(' if openmin else '['
                    ')' if openmax else ']'
                    assumption:
                    this is meant as the mathematical notation of intervals
                    '(' min does not belong to the interval
                    '[' min does belong to the interval
                    ')' max does not belong to the interval
                    ']' max does belong to the interval
        """
        hw_params = {}
        text = text.split('\n')
        in_block = False
        for line in text:
            if '--------------------' == line:
                if in_block:
                    break
                else:
                    in_block = True
                    continue
            if in_block:
                try:
                    key, value = line.split(':')
                    values = value.strip()
                    if (values[0] in '(['):
                        assert (values[-1] in '])'), \
                            "expected values string to end with either one " \
                            "of ']' or ')'"
                        opening_bracket = values[0]
                        closing_bracket = values[-1]
                        # an interval of integer values with min and max given
                        values = values[1:-1]    # strip brackets
                        values = values.split()  # split at blanks
                        assert (2 == len(values)), \
                            "expected exactly two values"
                        min, max = int(values[0]), int(values[1])

                        # start assumption ->
                        # assumption: the brackets are meant with their
                        # mathematical meaning
                        if opening_bracket == '(':
                            # min does not belong to the interval,
                            # thus min+1 belongs to the interval
                            min += 1
                        if closing_bracket == ')':
                            # max does not belong to the interval,
                            # thus max-1 belongs to the interval
                            max -= 1
                        # <- end assumption

                        # python range: min is included, max is not include
                        values = range(min, max+1)
                    else:
                        values = values.split()  # split at blanks
                        if 1 == len(values):
                            try:
                                # try to convert to int, if not, also ok
                                values = int(values[0])
                            except Exception:
                                pass
                    hw_params[key] = values
                except Exception as err:
                    print("WARNING: {} '{}'".format(err, line))
        return hw_params

    def rate_range_to_list(self, rate_range):
        rate_list = [i for i in self.sndrv_pcm_rates if i in rate_range]
        return rate_list

    def get_pcm_hw_params(self, pcm):
        hw_params = {}
        with open('/dev/null', 'w') as f:
            args = [self.executable, '-D', pcm, '--dump-hw-params', '-d', '1']
            if self.verbose:
                print(" ".join(s for s in args))
            p = subprocess.Popen(args, stdout=f, stderr=subprocess.PIPE)
            stdout, stderr = p.communicate()
            stderr = stderr.decode()
            errorlevel = p.returncode
            assert (stdout is None), \
                "expected stdout to be redirected to /dev/null"
            hw_params = self.parse_hw_params(stderr)
            if hw_params:
                hw_params['RATE'] = self.rate_range_to_list(hw_params['RATE'])
        return hw_params

    def get_capture_interfaces(self):
        interfaces = []
        pcms = ar.get_pcms()
        for pcm in pcms:
            # we are only interrested in the capabilities of the
            # "Direct hardware device without any conversions"
            if "hw:" != pcm[:3]:
                continue
            hw_params = self.get_pcm_hw_params(pcm)
            if hw_params:
                interfaces.append({
                    'device': pcm[3:],
                    'formats': hw_params['FORMAT'],
                    'rates':  hw_params['RATE'],
                    'channels': hw_params['CHANNELS'],
                })
        return interfaces


try:
    import alsaaudio
    ALSAAUDIO_IS_PRESENT = True

    # length of one sample in bytes
    FORMAT_LENGTHS = {
        alsaaudio.PCM_FORMAT_S8: 1,
        alsaaudio.PCM_FORMAT_U8: 1,
        alsaaudio.PCM_FORMAT_S16_LE: 2,
        alsaaudio.PCM_FORMAT_S16_BE: 2,
        alsaaudio.PCM_FORMAT_U16_LE: 2,
        alsaaudio.PCM_FORMAT_U16_BE: 2,
        alsaaudio.PCM_FORMAT_S24_LE: 4,     # 3 byte transferred as 4
        alsaaudio.PCM_FORMAT_S24_BE: 4,     # 3 byte transferred as 4
        alsaaudio.PCM_FORMAT_U24_LE: 4,     # 3 byte transferred as 4
        alsaaudio.PCM_FORMAT_U24_BE: 4,     # 3 byte transferred as 4
        alsaaudio.PCM_FORMAT_S32_LE: 4,
        alsaaudio.PCM_FORMAT_S32_BE: 4,
        alsaaudio.PCM_FORMAT_U32_LE: 4,
        alsaaudio.PCM_FORMAT_U32_BE: 4,
        alsaaudio.PCM_FORMAT_FLOAT_LE: 4,
        alsaaudio.PCM_FORMAT_FLOAT_BE: 4,
        alsaaudio.PCM_FORMAT_FLOAT64_LE: 8,
        alsaaudio.PCM_FORMAT_FLOAT64_BE: 8,
        alsaaudio.PCM_FORMAT_MU_LAW: 1,
        alsaaudio.PCM_FORMAT_A_LAW: 1,
        alsaaudio.PCM_FORMAT_IMA_ADPCM: 1,
        alsaaudio.PCM_FORMAT_MPEG: 1,
        alsaaudio.PCM_FORMAT_GSM: 1,
        alsaaudio.PCM_FORMAT_S24_3LE: 3,
        alsaaudio.PCM_FORMAT_S24_3BE: 3,
        alsaaudio.PCM_FORMAT_U24_3LE: 3,
        alsaaudio.PCM_FORMAT_U24_3BE: 3,
    }

    ALSAAUDIO_2_ASOUND_FORMATS = {
        alsaaudio.PCM_FORMAT_S8: 'S8',
        alsaaudio.PCM_FORMAT_U8: 'U8',
        alsaaudio.PCM_FORMAT_S16_LE: 'S16_LE',
        alsaaudio.PCM_FORMAT_S16_BE: 'S16_BE',
        alsaaudio.PCM_FORMAT_U16_LE: 'U16_LE',
        alsaaudio.PCM_FORMAT_U16_BE: 'U16_BE',
        alsaaudio.PCM_FORMAT_S24_LE: 'S24_LE',
        alsaaudio.PCM_FORMAT_S24_BE: 'S24_BE',
        alsaaudio.PCM_FORMAT_U24_LE: 'U24_LE',
        alsaaudio.PCM_FORMAT_U24_BE: 'U24_BE',
        alsaaudio.PCM_FORMAT_S32_LE: 'S32_LE',
        alsaaudio.PCM_FORMAT_S32_BE: 'S32_BE',
        alsaaudio.PCM_FORMAT_U32_LE: 'U32_LE',
        alsaaudio.PCM_FORMAT_U32_BE: 'U32_BE',
        alsaaudio.PCM_FORMAT_FLOAT_LE: 'FLOAT_LE',
        alsaaudio.PCM_FORMAT_FLOAT_BE: 'FLOAT_BE',
        alsaaudio.PCM_FORMAT_FLOAT64_LE: 'FLOAT64_LE',
        alsaaudio.PCM_FORMAT_FLOAT64_BE: 'FLOAT64_BE',
        alsaaudio.PCM_FORMAT_MU_LAW: 'MU_LAW',
        alsaaudio.PCM_FORMAT_A_LAW: 'A_LAW',
        alsaaudio.PCM_FORMAT_IMA_ADPCM: 'IMA_ADPCM',
        alsaaudio.PCM_FORMAT_MPEG: 'MPEG',
        alsaaudio.PCM_FORMAT_GSM: 'GSM',
        alsaaudio.PCM_FORMAT_S24_3LE: 'S24_3LE',
        alsaaudio.PCM_FORMAT_S24_3BE: 'S24_3BE',
        alsaaudio.PCM_FORMAT_U24_3LE: 'U24_3LE',
        alsaaudio.PCM_FORMAT_U24_3BE: 'U24_3BE',
    }

    ASOUND_2_ALSAAUDIO_FORMATS = {
        v: k for k, v in ALSAAUDIO_2_ASOUND_FORMATS.items()}

    class alsaaudio_tester():
        RESULTS = [
            'OK',
            'E_UNKNOWN',
            'E_ALSAAUDIO',
            'E_OVERRUN',
            'E_ZERO_LENGTH',
            'E_INVALID_LENGTH',
            'E_INVALID_DATA_LENGTH',
            'E_RECORDED_ALL_ZEROS',
            'E_MONO',
            'F_NOT_IMPLEMENTED']

        def __init__(self, verbose):
            self.pcm_devices = alsaaudio.pcms(alsaaudio.PCM_CAPTURE)
            # the numbering of these constants has to match
            # the corresponidng positon within RESULTS
            self.OK = 0
            self.E_UNKNOWN = 1
            self.E_ALSAAUDIO = 2
            self.E_OVERRUN = 3
            self.E_ZERO_LENGTH = 4
            self.E_INVALID_LENGTH = 5
            self.E_INVALID_DATA_LENGTH = 6
            self.E_RECORDED_ALL_ZEROS = 7
            self.E_MONO = 8
            self.F_NOT_IMPLEMENTED = 9
            self.verbose = verbose

        def test_configuration(
                self,
                pcm_device,
                rate,
                format,
                periodsize,
                channels):
            try:
                assert (channels in [1, 2]), \
                    f"expected one or two channels, got {channels}"
                samplesize = FORMAT_LENGTHS[format]
                framesize = samplesize * channels
                PCM = alsaaudio.PCM(
                    type=alsaaudio.PCM_CAPTURE,
                    mode=alsaaudio.PCM_NORMAL,
                    rate=rate,
                    channels=channels,
                    format=format,
                    periodsize=periodsize,
                    device=pcm_device
                )
                raw_data = b''
                t_start = time.time()
                while len(raw_data) < framesize * rate:
                    length, data = PCM.read()
                    if length > 0:
                        raw_data += data
                    """
                    In PCM_NORMAL mode, this function blocks until a full
                    period is available, and then returns a tuple (length,data)
                    where length is the number of frames of captured data, and
                    data is the captured sound frames as a string. The length
                    of the returned data will be periodsize*framesize bytes.

                    In case of an overrun, this function will return a negative
                    size: -EPIPE. This indicates that data was lost, even if
                    the operation itself succeeded. Try using a larger
                    periodsize.
                    """
                    if length < 0:
                        return self.E_OVERRUN, None, None, None
                    if length == 0:
                        return self.E_ZERO_LENGTH, None, None, None
                    if 0 != (length % periodsize):
                        # expecting an even multiple of periodsize
                        return self.E_INVALID_LENGTH, None, None, None
                    if (length * framesize) != len(data):
                        # number of frames multiplied with size of frames must
                        # be the size of the buffer
                        return self.E_INVALID_DATA_LENGTH, None, None, None
                t_end = time.time()
                t_duration = t_end - t_start

                assert (len(raw_data) >= (framesize * rate)), \
                    "expected number of bytes to be framesize * rate"
                asound_format = ALSAAUDIO_2_ASOUND_FORMATS[format]
                if asound_format == 'S16_LE':
                    unpacked_data = array(st_unpack(
                        "<%ih" % (rate * channels),
                        raw_data[:framesize * rate]))
                elif asound_format == 'S24_3LE':
                    unpacked_data = []
                    for i in range(rate * channels):
                        chunk = raw_data[i*3:i*3+3]
                        unpacked_data.append(st_unpack(
                            '<i',
                            chunk + (b'\0' if chunk[2] < 128 else b'\xff'))[0])
                    unpacked_data = array(unpacked_data)
                elif asound_format == 'S32_LE':
                    unpacked_data = array(st_unpack(
                        "<%ii" % (rate * channels),
                        raw_data[:framesize * rate]))
                else:
                    print(
                        "\tERROR: format conversion of '{}' is not implemented"
                        .format(asound_format))
                    return self.F_NOT_IMPLEMENTED, None, None, None
                assert (len(unpacked_data) == (rate * channels)), \
                    "expected number of samples to be sample rate * channels"
                # for 1 channel the format now is [left, ..., left]
                # for 2 channels the format now is [left, right,
                #                                   ..., left, right]

                if min(unpacked_data) == max(unpacked_data):
                    return self.E_RECORDED_ALL_ZEROS, None, None, None

                unpacked_data = unpacked_data.reshape((rate, channels))
                # for 1 channel the format now is [[left], ..., [left]]
                # for 2 channels the format now is [[left, right],
                #                                   ..., [left, right]]
                # left channel = unpacked_data[:, 0]
                # right channel = unpacked_data[:, 1]

                if ((2 == channels)
                        and (list(unpacked_data[:, 0])
                             == list(unpacked_data[:, 1]))):
                    return self.E_MONO, None, None, None

                # NFFT = 1024 for 44100 and 48000,
                #        2048 for 96000,
                #        4096 for 192000
                # -> the frequency resolution is constant
                NFFT = max(1024, 1024 * rate // 48000)

                peak_freq = []
                for channel in range(channels):
                    Pxx, freqs = mlab_psd(
                        unpacked_data[:, channel],
                        NFFT,
                        rate)
                    m = max(Pxx)
                    if m == min(Pxx):
                        peak_freq.append(None)
                    else:
                        pos = [i for i, j in enumerate(Pxx) if j == m]
                        peak_freq.append(freqs[pos][0])

                return self.OK, unpacked_data, t_duration, peak_freq
            except alsaaudio.ALSAAudioError as e:
                print("\tALSAAudioError {}".format(e))
                return self.E_ALSAAUDIO, None, None, None
            except Exception as e:
                print(type(e), e)
            return self.E_UNKNOWN, None, None, None

        def save_wav(self, file, channels, rate, format, data):
            if list == type(data):
                data = np.array(data)
            if 'S16_LE' == format:
                sample_width = 2
                min = -32768
                max = 32767
                format = '<h'
            elif 'S24_3LE' == format:
                sample_width = 4
                data = data * 0x100    # normalize to 32 bit
                min = -2147483648
                max = 2147483647
                format = '<i'
            elif 'S32_LE' == format:
                sample_width = 4
                min = -2147483648
                max = 2147483647
                format = '<i'
            else:
                print(
                    'WARNING: save_wav() format {} is not supported'
                    .format(format))
                return
            if self.verbose:
                print(file, len(data), data.min(), data.max())
            wf = wave.open(file, 'wb')
            wf.setnchannels(channels)
            wf.setsampwidth(sample_width)
            wf.setframerate(rate)
            for value in data.flatten():
                value = int(value)
                if value < min:
                    value = min
                if value > max:
                    value = max
                value = struct.pack(format, value)
                wf.writeframesraw(value)
            wf.close()

        def test(
                self,
                interfaces,
                periodsize,
                channels,
                regression,
                test_card,
                test_tone,
                save_wav,
                data_path):
            test_frequency = None
            if ((test_tone is not None)
                    and (len(test_tone) >= 8)
                    and ('external' == test_tone[0:8])):
                # suppress test tone generation if configured to be external
                st = None
                if ',' == test_tone[8]:
                    test_frequency = int(test_tone[9:])
            else:
                st = speaker_test(self.verbose)
                if st is None:
                    print(
                        "WARNING: 'speaker_test' instance could not be "
                        "created, there will be no frequency generated "
                        "for the loop back test")
            test_log = []
            tested_pcm_devices = []
            print(
                "audio_sampling_rate, Audio, Device, Format, PeriodSize, "
                "regression, channel, result[, duration]"
                "[, peak frequency / generated frequency = frequency ratio]")
            for pcm_device in self.pcm_devices:
                if test_card is not None:
                    if test_card not in pcm_device:
                        print('skip', pcm_device)
                        # if the card to be tested is configured but the
                        # current device doesn't match, skip the test
                        continue
                for interface in interfaces:
                    device = interface['device']
                    if device in BAD_DEVICES:
                        print('skip BAD_DEVICES', device)
                        continue    # prevent a core dump
                    if (((device in pcm_device)
                            or (device[:device.find(',DEV=')] in pcm_device))
                            and (pcm_device not in tested_pcm_devices)):
                        tested_pcm_devices.append(pcm_device)
                        for rate in interface['rates']:
                            generated_frequency = test_frequency
                            if st is not None:
                                generated_frequency = rate // 3
                                st.start_test_tone(
                                    # preferably use the device configured for
                                    # the test tone
                                    test_tone if test_tone is not None

                                    # else fall back to the same device which
                                    # is tested
                                    else device,

                                    # use the same sample rate as for the
                                    # capturing
                                    rate,

                                    # adapt the frequency to the sample rate,
                                    # theoretical max would be (rate / 2)
                                    generated_frequency
                                )
                            for format in interface['formats']:
                                asound_format = format
                                alsaaudio_format = \
                                    ASOUND_2_ALSAAUDIO_FORMATS[asound_format]
                                for i in range(regression):
                                    result, data, duration, peak_freq = \
                                        self.test_configuration(
                                            pcm_device,
                                            rate,
                                            alsaaudio_format,
                                            periodsize,
                                            channels)
                                    for channel in range(channels):
                                        peak_frequency = None \
                                            if (peak_freq is None) \
                                            else peak_freq[channel]
                                        frequency_ratio = None \
                                            if ((peak_frequency is None)
                                                or (generated_frequency
                                                    is None)) \
                                            else (peak_frequency
                                                  / generated_frequency)
                                        test_log.append({
                                            'Device': pcm_device,
                                            'audio_sampling_rate': rate,
                                            'Format': asound_format,
                                            'PeriodSize': periodsize,
                                            'i': i + 1,
                                            'channel': channel,
                                            'result': result,
                                            'duration': duration,
                                            'peak_frequency': peak_frequency,
                                            'generated_frequency':
                                                generated_frequency,
                                            'frequency_ratio': frequency_ratio,
                                        })

                                        print(
                                            "{:6d}, "       # rate
                                            "alsaaudio, "
                                            "{}, "          # pcm_device
                                            "{:7s}, "       # asound_format
                                            "{}, "          # periodsize
                                            "{:2d}, "       # i+1
                                            "{}, "          # channel
                                            "{}"            # result
                                            "{}"            # duration
                                            "{}"            # peak_frequency
                                            "{}"            # frequency_ratio
                                            .format(
                                                rate,
                                                pcm_device,
                                                asound_format,
                                                periodsize,
                                                i+1,
                                                channel,
                                                self.RESULTS[result],

                                                "" if duration is None
                                                else ', {:.2f} s'
                                                .format(duration),

                                                "" if peak_frequency is None
                                                else ", {} Hz"
                                                .format(int(peak_frequency)),

                                                "" if frequency_ratio is None
                                                else " / {} Hz = {:5.3f}"
                                                .format(
                                                    generated_frequency,
                                                    frequency_ratio)))
                                    if data is not None and save_wav:
                                        file = os.path.join(
                                            data_path,
                                            "fad_{}_{}_{}_{}_{}.wav"
                                            .format(
                                                slugify(pcm_device),
                                                rate,
                                                format,
                                                periodsize,
                                                i))
                                        self.save_wav(
                                            file,
                                            channels,
                                            rate,
                                            format,
                                            data)
                                    if result != self.OK:
                                        # speed up if the result is not ok,
                                        # break the regression
                                        break
                            if st is not None:
                                st.stop_test_tone()
            print()
            print('This is the list of untested devices:')
            pprint(set(self.pcm_devices) - set(tested_pcm_devices))
            if test_tone != "external":
                print()
                self.test_summary(test_log, regression, channels)

        def test_summary(self, test_log, regression, channels):
            # convert the entire results list
            df = pd.DataFrame(test_log)

            # drop all rows containing no values e.g. no duration,
            # no peak_frequency, no frequency_ratio
            df = df.dropna()

            # drop frequency_ratio deviating more than 2 %% from the ideal 1.0
            df = df[
                (df['frequency_ratio'] >= 0.998) &
                (df['frequency_ratio'] <= 1.002)]

            # in the brute force operation it has been observed that devices
            # appear to work with higher sample rates than supported, the
            # recording time is then i.e. 4 sec for a 48000 device tested as
            # 192000
            df = df[
                (df['duration'] > 0.9) &
                (df['duration'] < 1.1)]
            df['candidate'] = None
            num_candidates = 0
            for Device in df['Device'].unique():
                for audio_sampling_rate in df['audio_sampling_rate'].unique():
                    for Format in df['Format'].unique():
                        for PeriodSize in df['PeriodSize'].unique():
                            index = df[
                                (df['Device'] == Device) &
                                (df['audio_sampling_rate']
                                    == audio_sampling_rate) &
                                (df['Format'] == Format) &
                                (df['PeriodSize'] == PeriodSize)].index
                            if len(index) == regression * channels:
                                num_candidates += 1
                                df.loc[index, 'candidate'] = num_candidates

            if num_candidates >= 1:
                print("{} candidates found.".format(num_candidates))
                print("""Prefer candidates with these properties:
- audio_sampling_rate = highest available value
- Format = the more bits the better (32 better than 24, 24 better than 16)

This is the list of candidates fulfilling the minimum requirements:""")
                # drop all non-candidates
                df = df.dropna()

                # drop all but one line per setting
                df = df[(df['i'] == regression) & ((df['channel'] == 0))]
                df = df.reset_index(drop=True)

                # display all candidates
                pd.set_option('display.max_rows', None)
                print(df[[
                    'Device',
                    'audio_sampling_rate',
                    'Format',
                    'PeriodSize']])
                print()

                audio_sampling_rate = df['audio_sampling_rate'].max()
                Format = df['Format'].max()
                index = df[
                    (df['audio_sampling_rate'] == audio_sampling_rate) &
                    (df['Format'] == Format)].index
                if 1 == len(index):
                    print(
                        "This is the supersid.cfg setting of the best "
                        "candidate:")
                else:
                    print(
                        "These are the supersid.cfg settings of the best "
                        "candidates:")
                for Device in df['Device'].unique():
                    for PeriodSize in df['PeriodSize'].unique():
                        index = df[
                            (df['Device'] == Device) &
                            (df['audio_sampling_rate']
                                == audio_sampling_rate) &
                            (df['Format'] == Format) &
                            (df['PeriodSize'] == PeriodSize)].index
                        if (len(index)):
                            print("# candidate '{}', {}, {}, {}".format(
                                Device,
                                audio_sampling_rate,
                                Format,
                                PeriodSize))
                            print('[PARAMETERS]')
                            print('audio_sampling_rate = {}'.format(
                                audio_sampling_rate))
                            print('[Capture]')
                            print('Audio = alsaaudio')
                            print('Device = {}'.format(Device))
                            print('Format = {}'.format(Format))
                            print('PeriodSize = {}'.format(PeriodSize))
                            print()
            else:
                print("""No candidate could be found.

Q: Did you use an external frequency generator?
y: The candidate suggestion doesn't work with an external frequency generator.
n: Continue reading ...

Q: Have line out and line in of the audio cards been connected with an audio
   cable?
n: The candidate suggestion doesn't work without the loop back from line out to
   line in.
y: Doublecheck the cable is ok and correctly plugged in. Continue reading ...

Q: Is the line out generatin a test tone?
   Connect a speaker.
   Use the command below and replace the device name with the one to be
   verified.
   python3 isine.py -Dplughw:CARD=Generic,DEV=0 -f 440
n: Try command line options -t/--test-tone and -d/--device
   Connect line out of the -t interface with line in of the -d interface.
y: Continue reading ...

Q: Is the user who is executing the scripts part of the audio group?
   grep audio /etc/group
n: It may be worth adding the user to the audio group.
   sudo usermod -a -G audio
   logout and login in order to have the changes take effect
y: Continue reading ...

The device may not be suitable, the drivers may not be up to date, ...
Ask a search engine or an expert for help about fixing audio issues.""")

except ImportError:
    print(
        "ERROR: 'alsaaudio' is not available, on Linux try "
        "'python3 -m pip install alsaaudio'")
    ALSAAUDIO_IS_PRESENT = False


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        formatter_class=RawTextHelpFormatter,
        description="""
Test the audio capturing capability with the python module 'alsaaudio'.
Combinations of device, sampling-rate, format, periodsitze are tested. The hw
capabilities will be queried from 'arecord' unless -b/--brute-force is set.
""".format(__file__))
    parser.add_argument(
        "-c", "--config",
        dest="cfg_filename",
        type=exist_file,
        default=CONFIG_FILE_NAME,
        help="Supersid configuration file")
    parser.add_argument(
        "-b", "--brute-force",
        help="brute force test all 'alsaaudio' PCMs",
        action='store_true')
    parser.add_argument(
        "-n", "--channels",
        help="number of channels, default=1",
        choices=[1, 2],
        type=int,
        default=1)
    parser.add_argument(
        "-l", "--list",
        help="list the parameter combinations and exit",
        action='store_true')
    parser.add_argument(
        "-p", "--periodsize",
        help="""periodsize parameter of the PCM interface
default=1024, if the computer runs out of memory,
select smaller numbers like 128, 256, 512, ...""",
        type=int,
        default=1024)
    parser.add_argument(
        "-r", "--regression",
        help="regressions with the same settings, default=10",
        type=int,
        default=10)
    parser.add_argument(
        "-t", "--test-tone",
        help='''Format: "external" or "external,10000" or "CARD=xxxx",
the device to be used for the test tone generation.
If not set a loopback from DEVICE line out to DEVICE line in is expected.
''',
        default=None)
    parser.add_argument(
        "-d", "--device",
        help='Format: "CARD=xxxx", the device to be tested',
        default=None)
    parser.add_argument(
        "-s", "--save-wav",
        help="save wav files of the 1 second recordings",
        action='store_true')
    parser.add_argument(
        "-v", "--verbose",
        help="verbose output",
        action='store_true')
    args = parser.parse_args()

    config = readConfig(args.cfg_filename)

    t_start = time.time()

    if args.test_tone or args.device:
        if args.test_tone is None:
            args.test_tone = args.device
            print("setting -t/--test-tone={}".format(args.device))
        if args.device is None:
            print("-t/--test-tone requires -d/--device")
            sys.exit(1)

    if args.list:
        if ALSAAUDIO_IS_PRESENT:
            device_list = alsaaudio.pcms(alsaaudio.PCM_CAPTURE)
            print("List of 'alsaaudio' PCMs:")
            for device in device_list:
                print("\t{}".format(device))
            print()
        else:
            print(
                "ERROR: 'alsaaudio' is not available.\n"
                "Option -l/--list is not fully functional.")

    interfaces = []
    if args.brute_force:
        if ALSAAUDIO_IS_PRESENT:
            device_list = alsaaudio.pcms(alsaaudio.PCM_CAPTURE)
            for device in device_list:
                interfaces.append({
                    'device': device,
                    'rates': DEFAULT_RATES,
                    'formats': DEFAULT_FORMATS,
                    'channels': DEFAULT_CHANNELS,
                })
        else:
            print(
                "ERROR: 'alsaaudio' is not available.\n"
                "Option -b/--brute-force is not available.")
    else:
        ar = arecord(args.verbose)
        if ar is None:
            print("ERROR: arecord instance could not be created")
            sys.exit(1)
        else:
            interfaces = ar.get_capture_interfaces()

    for interface in interfaces:
        print(interface['device'])
        print('\trates:', interface['rates'])
        print('\tformats:', interface['formats'])
        print('\tchannels:', interface['channels'])

    if args.list:
        sys.exit(0)

    print()
    if ALSAAUDIO_IS_PRESENT:
        alsaaudio_tester(args.verbose).test(
            interfaces,
            args.periodsize,
            args.channels,
            args.regression,
            args.device,
            args.test_tone,
            args.save_wav,
            config.data_path)
    else:
        print(
            "ERROR: 'alsaaudio' is not available.\n"
            "The alsaaudio test is not available.")

    print("spent {} seconds".format(int(time.time() - t_start)))
