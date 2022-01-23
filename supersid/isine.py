#!/usr/bin/env python3

# based on
# https://raw.githubusercontent.com/larsimmisch/pyalsaaudio/master/isine.py

import sys
from threading import Thread
from multiprocessing import Queue
from queue import Empty
from math import pi, sin
import struct
import alsaaudio
import argparse


class SinePlayer(Thread):
    def __init__(self, device, rate, frequency, channels):
        Thread.__init__(self)
        self.setDaemon(True)
        self.channels = channels
        self.format = alsaaudio.PCM_FORMAT_S16_LE
        self.samplesize = 2    # number of bytes for self.format (1 channel)
        self.framesize = self.samplesize * self.channels
        self.rate = rate
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
