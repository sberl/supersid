#!/usr/bin/env python3

# based on
# https://raw.githubusercontent.com/larsimmisch/pyalsaaudio/master/isine.py

import sys
from threading import Thread
from multiprocessing import Queue
from queue import Empty
from math import pi, sin
import struct
try:
    import alsaaudio
except ImportError:
    sys.exit(
        "ERROR: 'alsaaudio' is not available, on Linux try "
        "'python3 -m pip install alsaaudio'")
import argparse

# http://larsimmisch.github.io/pyalsaaudio/libalsaaudio.html#pcm-objects
# It says: class alsaaudio.PCM "... will construct a PCM object with the given
# settings." This is not the truth. As of today (Jan 23, 2022) version 0.9.0
# is the latest available at pypi.org. This version is from Jul 13, 2020.
#
# The pyalsaaudio implementation as of this date is here:
# https://github.com/larsimmisch/pyalsaaudio/blob/5302dc524d5eccf27b74d0a80ee151452797818a/alsaaudio.c
# alsapcm_setup() linw 399 to 406 documents, that format, channels, rate, and
# periodsize may actually be different from the requested settings.
# Even worse: There is no function which would allow to query the actual
# setting. PCM.dumpinfo() allows to print thecsettings to stdout. A super
# clever solution. This output cannot be handled in the script. Lately the
# method PCM.info() has been added, but this is not available in the
# published 0.9.0.
#
# The only way to get hold of the actual values for channel, format, rate and
# periodsize is the use of the deprecated methods PCM.setchannels(),
# PCM.setformat(), PCM.setrate() and PCM.setperiodsize().
# With an USB SoundBlaster and an USB Behringer this worked, but selecting an
# unsupported number of channels for 'VIA USB Dongle' kills the dongle and
# along with it the script. It needs an unplug/plug cycle to recover.
#
# The third attempt is to open the device, query it's capabilities and select
# only values it can work with. If a value cannot be selected, that is
# required, then throw an exception.


class SinePlayer(Thread):
    def __init__(self, device, rate, frequency, channels):
        Thread.__init__(self)
        self.setDaemon(True)

        # preliminary open the device t query it's capabilities
        self.device = alsaaudio.PCM(device=device)

        # check channels
        supported_channels = self.device.getchannels()
        if channels not in supported_channels:
            channels = supported_channels[0]
        if(channels not in [1, 2]):
            err = f"PCM channels {channels} not in [1, 2]"
            raise ValueError(err)
        self.channels = channels

        # check format
        supported_formats = self.device.getformats()
        if('S16_LE' not in supported_formats):
            err = "PCM format 'S16_LE' is not supported"
            raise ValueError(err)
        self.format = alsaaudio.PCM_FORMAT_S16_LE
        self.samplesize = 2    # number of bytes for 'S16_LE' (1 channel)
        self.framesize = self.samplesize * self.channels

        # check rate
        supported_rates = self.device.getrates()
        if list == type(supported_rates):
            if rate not in supported_rates:
                err = f"PCM rate {rate} is not supported"
                raise ValueError(err)
        elif tuple == type(supported_rates):
            lower, higher = supported_rates
            if (rate >= lower) and ((higher == -1) or (rate <= higher)):
                pass
            else:
                err = f"PCM rate {rate} is not supported"
                raise ValueError(err)
        else:
            f"PCM rates type {type(supported_rates)} is not implemented"
            raise NotImplementedError(err)
        self.rate = rate

        # close preliminary opened device
        self.device.close()

        self.frequency = self.nearest_frequency(frequency)
        buffer = self.generate()
        assert (0 == (len(buffer) % self.framesize)), \
            "expected length of the buffer to be a multiple of the frame size"

        if self.frequency > self.rate / 2:
            raise ValueError('maximum frequency is %d' % (self.rate / 2))

        self.device = alsaaudio.PCM(
            channels=self.channels,
            format=self.format,
            rate=self.rate,
            periodsize=len(buffer) // self.framesize,
            device=device)

        self.queue = Queue()
        self.queue.put(buffer)
        self._running = False

    def nearest_frequency(self, frequency):
        # calculate the nearest frequency where the wave form fits into the
        # buffer in other words, select f so that sampling_rate/f is an integer
        return float(self.rate) / int(self.rate / frequency)

    def generate(self, duration=0.125):
        # generate a buffer with a sine wave of `frequency`
        # that is approximately `duration` seconds long

        # the buffersize we approximately want
        target_size = int(self.rate * self.samplesize * duration)

        # the length of a full sine wave at the frequency
        cycle_size = int(self.rate / self.frequency)

        # number of full cycles we can fit into target_size
        factor = int(target_size / cycle_size)

        size = max(int(cycle_size * factor), 1)

        mono = [int(
            0.1     # limit the amplitude to 10%
            * 32767
            * sin(2 * pi * self.frequency * i / self.rate))
            for i in range(size)]

        if self.channels == 1:
            sine = mono
        elif self.channels == 2:
            sine = []
            for val in mono:
                sine.append(val)    # left channel
                sine.append(val)    # right channel
        else:
            assert False, f"supporting 1 or 2 channels, found {self.channels}"

        return struct.pack('%dh' % size * self.channels, *sine)

    def run(self):
        buffer = None
        self._running = True
        while self._running:
            try:
                buffer = self.queue.get(False)
                self.device.write(buffer)
            except Empty:
                if buffer:
                    self.device.write(buffer)

    def stop(self):
        self._running = False
        self.join()


def main():
    import time
    parser = argparse.ArgumentParser("simplified spear-test application")
    parser.add_argument(
        '-D', '--device',
        help='playback device')
    parser.add_argument(
        '-r', '--rate',
        help='stream rate in Hz',
        type=int,
        default=48000)
    parser.add_argument(
        '-f', '--frequency',
        help='sine wave frequency in Hz',
        type=int,
        default=440)
    parser.add_argument(
        "-n", "--channels",
        help="number of channels, default=1",
        choices=[1, 2],
        type=int,
        default=1)
    args = parser.parse_args()
    print(args)

    isine = SinePlayer(args.device, args.rate, args.frequency,
                       args.channels)
    isine.start()
    time.sleep(2)
    isine.stop()
    del(isine)

    time.sleep(0.5)

    isine = SinePlayer(args.device, args.rate, args.frequency // 2,
                       args.channels)
    isine.start()
    time.sleep(2)
    isine.stop()
    del(isine)


if __name__ == '__main__':
    main()
