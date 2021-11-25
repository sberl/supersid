#!/usr/bin/env python3

import os
import sys
import re
import glob
import time
import argparse
from argparse import RawTextHelpFormatter
import pkg_resources    # python3 -m pip install setuptools
from struct import unpack as st_unpack
from numpy import array
from matplotlib.mlab import psd as mlab_psd
from pprint import pprint


if __name__ == '__main__':
    print("Version 202111250812")


"""
1) walk through /proc/asound in order to identify the audio capture devices and their native capabilities
   https://alsa.opensrc.org/Proc_asound_documentation
   https://www.kernel.org/doc/html/latest/sound/designs/procfile.html
2) walk through alsaaudio pcms and test with the capabilities of the capture devices known from /proc/asound
"""

DEFAULT_RATES = [44100, 48000, 96000, 192000]
DEFAULT_FORMATS = ['S16_LE', 'S24_3LE', 'S32_LE']
DEFAULT_CHANNELS = 1    # actually we don't know but lets assume there is at least one channel

AUDIO_FORMATS = [
    'S8', 'U8',
    'S16_LE', 'S16_BE', 'U16_LE', 'U16_BE',
    'S24_LE', 'S24_BE', 'U24_LE', 'U24_BE',
    'S32_LE',  'S32_BE', 'U32_LE', 'U32_BE',
    'FLOAT_LE', 'FLOAT_BE', 'FLOAT64_LE', 'FLOAT64_BE',
    'MU_LAW', 'A_LAW', 'IMA_ADPCM', 'MPEG', 'GSM',
    'S24_3LE', 'S24_3BE', 'U24_3LE', 'U24_3BE',
]

FORMAT_MASK = {
    # bits [0x2]: 16
    # bits [0x6]: 16 20
    # bits [0xe]: 16 20 24
    # bits [0x1e]: 16 20 24 32
    0x02: 'S16_LE',     # 16 bits are sure, but S/U or LE/BE?
    0x04: 'S20_LE',     # 20 bits are sure, but S/U or LE/BE?
    0x08: 'S24_3LE',    # 24 bits are sure, but S/U or LE/BE?
    0x10: 'S32_LE',     # 32 bits are sure, but S/U or LE/BE?
#    0x20: 'S24_3BE',    # 24 bits are sure, but S/U or LE/BE/3LE/3BE?
}

RATES_MASK = {
    0x400: 192000,
    0x100:  96000,
    0x040:  48000,
    0x020:  44100,
    0x010:  32000,
}


class proc_asound_walker():
    def __init__(self, test_dir=None):
        self.zip_proc_asound = False
        if test_dir:
            self.proc_path = os.path.normpath(os.path.join(test_dir, 'proc'))
        else:
            self.proc_path = '/proc'

    def check_preconditions(self):
        if os.path.isdir(self.proc_path):
            asound_path = os.path.normpath(os.path.join(self.proc_path, 'asound'))
            if os.path.isdir(asound_path):
                print("reading {}".format(asound_path))
                return True
            else:
                print("\tERROR: '{}' not found".format(asound_path))
                self.zip_proc_asound = True
        else:
            print("\tERROR: '{}' not found".format(self.proc_path))
            self.zip_proc_asound = True
        return False

    def read_file(self, file):
        lines = ''
        if os.path.isfile(file):
            with open(file, 'r') as f:
                lines = f.read().split('\n')
        return(lines)

    def read_cards(self):
        """
        expected format:
         index [the id string]: short description
                                long description
        example:
         0 [HDMI           ]: HDA-Intel - HDA ATI HDMI
                              HDA ATI HDMI at 0xfeb64000 irq 46
         1 [Generic        ]: HDA-Intel - HD-Audio Generic
                              HD-Audio Generic at 0xfeb60000 irq 47
         2 [U0x41e0x30d3   ]: USB-Audio - USB Device 0x41e:0x30d3
                              USB Device 0x41e:0x30d3 at usb-0000:00:10.0-3, full speed
        """
        cards = {}
        cards_path = os.path.normpath(os.path.join(self.proc_path, 'asound/cards'))
        if os.path.isfile(cards_path):
            lines = self.read_file(cards_path)
            while (len(lines) >= 2):
                # interpret first line
                index_id_short_description = lines[0]
                separator_1 = index_id_short_description.find('[')
                separator_2 = index_id_short_description.find(']:')
                index = int(index_id_short_description[:separator_1].strip())
                id = index_id_short_description[separator_1+1:separator_2].strip()
                short_description = index_id_short_description[separator_2+2:].strip()
                # interpret second line
                long_description = lines[1].strip()
                # drop interpreted lines
                lines = lines[2:]
                # store result
                cards[index] = {'id': id, 'short_description': short_description, 'long_description': long_description}
            for line in lines:
                if line.strip():
                    print("\tWARNING: unexpected line '{}'".format(line))
                    self.zip_proc_asound = True
        else:
            print("\tERROR: '{}' not found".format(cards_path))
            self.zip_proc_asound = True
        return cards

    def sanity_check(self, interface):
        """fill keys/value pairs with defaults, if the keys are not present"""
        assert('card' in interface)
        if 'formats' not in interface:
            interface['formats'] = DEFAULT_FORMATS
            print("\tWARNING: maiking up 'formats' for card '{}'".format(interface['card']))
            self.zip_proc_asound = True
        if 'channels' not in interface:
            interface['channels'] = DEFAULT_CHANNELS
            print("\tWARNING: maiking up 'channels' for card '{}'".format(interface['card']))
            self.zip_proc_asound = True
        if 'rates' not in interface:
            interface['rates'] = DEFAULT_RATES
            print("\tWARNING: maiking up 'rates' for card '{}'".format(interface['card']))
            self.zip_proc_asound = True
        return(interface)

    def get_capture_interfaces_from_stream(self, file, card):
        print("\t{}".format(file))
        lines = self.read_file(file)
        interfaces = []
        interface = None
        inCaptureSection = False
        for line in lines[1:]:
            if line[:7] == 'Capture':
                inCaptureSection = True
            elif line[:8] == 'Playback':
                inCaptureSection = False
            if inCaptureSection:
                line = line.split()
                if line:
                    if (2 == len(line)) and (line[0] == 'Interface'):
                        # distinguish between (len(line) == 3)
                        """
                        Status: Running
                            Interface = 5
                            Altset = 3
                            URBs = 2 [ 1 1 ]
                            Packet Size = 200
                            Momentary freq = 44,099 Hz
                        """
                        # and (len(line) == 2)
                        """
                        Interface 5
                            Altset 1
                            Format: S24_3LE
                            Channels: 2
                            Endpoint: 6 IN (ASYNC)
                            Rates: 48001 - 96000 (continous)
                        """
                        if interface:
                            interfaces.append(self.sanity_check(interface))
                        interface = {'card': 'CARD={}'.format(card['id']), 'number': int(line[1])}
                    elif line[0] == 'Format:':
                        if (2 == len(line)) and [line[1] in AUDIO_FORMATS]:
                            interface['formats'] = [line[1]]
                        elif (4 == len(line)) and ('(' == line[2][0]) and ('bits)' == line[3]):
                            print("\tWARNING: guessing format '{}'".format(" ".join(line)))
                            bits = line[2][1:]  # TODO: clarify the mapping from line[1] (hex representation) to ALSA audio formats
                            if '8' == bits:
                                interface['formats'] = ['S8']
                            elif '16' == bits:
                                interface['formats'] = ['S16_LE']
                            elif '24' == bits:
                                interface['formats'] = ['S24_3LE']
                            elif '32' == bits:
                                interface['formats'] = ['S32_LE']
                            else:
                                print("\tERROR: can't interpret '{}'".format(" ".join(line)))
                    elif line[0] == 'Channels:':
                        assert(2 == len(line))
                        interface['channels'] = int(line[1])
                    elif line[0] == 'Rates:':
                        assert(2 <= len(line))
                        if (5 == len(line)) and \
                           (line[2] == '-') and \
                           (line[-1] in ['(continous)', '(continuous)']):
                            # https://alsa-devel.alsa-project.narkive.com/OJHvIzOP/correction-audiophile-usb-stream0-output
                            # Rates: 48001 - 96000 (continous)
                            # Rates: 48001 - 96000 (continuous)
                            min_rate = int(line[1])
                            max_rate = int(line[3])
                            interface['rates'] = [min_rate]
                            for rate in DEFAULT_RATES:
                                if (rate > min_rate) and (rate < max_rate):
                                    interface['rates'].append(rate)
                            interface['rates'].append(max_rate)
                        else:
                            # Rates: 44100, 48000, 88200, 96000, 176400, 192000
                            interface['rates'] = [int(i.strip(',')) for i in line[1:]]
        if interface:
            interfaces.append(self.sanity_check(interface))
        return interfaces

    def get_capture_interfaces_from_codec(self, file, card):
        print("\t{}".format(file))
        lines = self.read_file(file)
        interfaces = []
        interface = None
        inCaptureSection = False
        inPcmSection = False
        for line in lines:
            if re.search('^Node 0x[0-9a-fA-F]+ \[Audio Input\]', line):
                inCaptureSection = False
                inPcmSection = False
                if interface:
                    interfaces.append(self.sanity_check(interface))
                if ': Stereo Amp-In' in line:
                    interface = {'card': 'CARD={}'.format(card['id']), 'channels': 2}
                    inCaptureSection = True
                elif ': Stereo Digital' in line:
                    interface = None
                else:
                    interface = None
                    print("\tERROR: can't interpret '{}'".format(line))
            elif re.search('^Node 0x[0-9a-fA-F]+', line):
                inCaptureSection = False
                inPcmSection = False
            if inCaptureSection:
                if '  PCM:' == line[:6]:
                    inPcmSection = True
                    if ('rates' in line) and ('bits' in line):
                        # sinlge line PCM section with all in one line
                        # PCM: rates 0x160, bits 0x06, types 0x1
                        tmp = line.split(',')
                        for t in tmp:
                            t = t.split()
                            if t[-2] == 'rates':
                                interface['rates'] = []
                                rates = int(t[-1], 16)
                                for r in RATES_MASK:
                                    if rates & r:
                                        interface['rates'].append(RATES_MASK[r])
                                        rates ^= r
                                if rates:
                                    print("\tERROR: could not convert some rates 0x{:X}".format(rates))
                            elif t[-2] == 'bits':
                                interface['formats'] = []
                                bits = int(t[-1], 16)
                                for b in FORMAT_MASK:
                                    if bits & b:
                                        interface['formats'].append(FORMAT_MASK[b])
                                        bits ^= b
                                if bits:
                                    print("\tERROR: could not convert some formats 0x{:X}".format(bits))
                        inPcmSection = False
                elif re.search('^  [A-Za-z0-9_]', line):
                    if inPcmSection:
                        inPcmSection = False
                if inPcmSection:
                    # multiline PCM section with rates and bits in separate lines
                    if re.search('^    rates \[0x[0-9a-fA-F]+\]:', line):
                        rates = line[line.find(':')+1:].split()
                        interface['rates'] = [int(r) for r in rates]
                    elif re.search('^    bits \[0x[0-9a-fA-F]+\]:', line):
                        bits = line[line.find(':')+1:].split()
                        bits = [int(b) for b in bits]
                        interface['formats'] = []
                        for b in bits: # TODO: clarify the mapping from the hex representation to ALSA audio formats
                            if 8 == b:
                                interface['formats'].append('S8')
                            elif 16 == b:
                                interface['formats'].append('S16_LE')
                            elif 24 == b:
                                interface['formats'].append('S24_3LE')
                            elif 32 == b:
                                interface['formats'].append('S32_LE')
                            else:
                                print("\tWARNING: unsupported bit length of {} bits".format(b))

        if interface:
            interfaces.append(self.sanity_check(interface))
        return interfaces

    def consolidate_interfaces(self, interfaces):
        consolidated_interfaces = []
        for i in interfaces:
            isAppended = False
            i['formats'] = sorted(i['formats'])
            i['rates'] = sorted(i['rates'])
            for idx, ci in enumerate(consolidated_interfaces):
                if (i['card'] == ci['card']) and (i['channels'] == ci['channels']):
                    # card with the same name and the same amount of channels is present
                    if set(i['formats']) == set(ci['formats']):
                        # the same formats are accepted, join the rates
                        consolidated_interfaces[idx]['rates'] = list(set(i['rates'] + ci['rates']))
                        isAppended = True
                    elif set(i['rates']) == set(ci['rates']):
                        # the same rates are accepted, join the formats
                        consolidated_interfaces[idx]['formats'] = list(set(i['formats'] + ci['formats']))
                        isAppended = True
            if not isAppended:
                consolidated_interfaces.append(i)
        return consolidated_interfaces

    def get_capture_interfaces(self):
        interfaces = []
        if self.check_preconditions():
            cards = self.read_cards()
            for index in cards:
                folder = os.path.normpath('{}/asound/card{}'.format(self.proc_path, index))
                if os.path.isdir(folder):
                    pcm_play = glob.glob(os.path.normpath(os.path.join(folder, 'pcm*p/sub*')))
                    play = []
                    for p in pcm_play:
                        p = os.path.normpath(p).split(os.sep)
                        # print(p)
                        play.append("{}/{}".format(p[-2], p[-1]))
                    pcm_capture = glob.glob(os.path.normpath(os.path.join(folder, 'pcm*c/sub*')))
                    capture = []
                    for p in pcm_capture:
                        p = os.path.normpath(p).split(os.sep)
                        # print(p)
                        capture.append("{}/{}".format(p[-2], p[-1]))
                    if (0 == len(pcm_play)) and (0 == len(pcm_capture)):
                        print("\tERROR: There are neither replay nor capture interfaces present.")
                        self.zip_proc_asound = True
                    print("\t{} playback: {}, capture: {}".format(folder, play, capture))

                    # USB Audo Streams: card*/stream*
                    # Shows the assignment and the current status of each audio stream of the given card.
                    usb_interfaces_found = 0
                    streams = glob.glob(os.path.join(folder, 'stream*'))
                    for stream in streams:
                        if os.path.isfile(stream):
                            new_interfaces = self.get_capture_interfaces_from_stream(stream, cards[index])
                            interfaces += new_interfaces
                            interface_numbers = []
                            for interface in new_interfaces:
                                interface_numbers.append(interface['number'])
                            usb_interfaces_found += len(set(interface_numbers))
                        else:
                            print("\tERROR: '{}' is no file".format(stream))
                            self.zip_proc_asound = True

                    # HD-Audio Codecs: card*/codec#*
                    # Shows the general codec information and the attribute of each widget node.
                    hd_interfaces_found = 0
                    codecs = glob.glob(os.path.join(folder, 'codec#*'))
                    for codec in codecs:
                        if os.path.isfile(codec):
                            new_interfaces = self.get_capture_interfaces_from_codec(codec, cards[index])
                            interfaces += new_interfaces
                            hd_interfaces_found += len(new_interfaces)
                        else:
                            print("\tERROR: '{}' is no file".format(codec))
                            self.zip_proc_asound = True

                    # AC97 Codec Information: card*/codec97#*/ac97#?-?
                    # Shows the general information of this AC97 codec chip, such as name, capabilities, set up.
                    AC97_interfaces_found = 0
                    codecs = glob.glob(os.path.join(folder, 'codec97#*/ac97#?-?'))
                    for codec in codecs:
                        if os.path.isfile(codec):
                            print('\tTODO', codec)
                            self.zip_proc_asound = True
                        else:
                            print("\tERROR: '{}' is no file".format(codec))
                            self.zip_proc_asound = True

                    if len(pcm_capture) != (usb_interfaces_found + hd_interfaces_found + AC97_interfaces_found):
                        print("\tERROR: '{}' has a mismatch regarding the number of capture devices.".format(folder))
                        print("\t\tnumber of 'pcm*c' sub folders is {}".format(len(pcm_capture)))
                        print("\t\tnumber of capture devices in 'stream*' files is {}".format(usb_interfaces_found))
                        print("\t\tnumber of capture devices in 'codec#*' files is {}".format(hd_interfaces_found))
                        # TODO print("\t\tnumber of capture devices in 'TODO' files is {}".format(AC97_interfaces_found))
                        self.zip_proc_asound = True
                else:
                    print("\tERROR: '{}' not found".format(folder))
                    self.zip_proc_asound = True

        consolidated_interfaces = self.consolidate_interfaces(interfaces)
        while (consolidated_interfaces != interfaces):
            interfaces = consolidated_interfaces
            consolidated_interfaces = self.consolidate_interfaces(interfaces)

        if self.zip_proc_asound:
            self.print_zip()

        return consolidated_interfaces

    def print_zip(self):
        print("""
    +-----------------------------------------------------------------------+
    | Something unexpected happened while parsing the folder structure      |
    |   /proc/asound                                                        |
    | You may help improving the program by providing the folder content.   |
    | The format of the folder is specified here:                           |
    |   https://alsa.opensrc.org/Proc_asound_documentation                  |
    |   https://www.kernel.org/doc/html/latest/sound/designs/procfile.html  |
    | There should be no secrets in the information I ask for.              |
    | Please do the following in a shell:                                   |
    |                                                                       |
    |   cd /tmp                                                             |
    |   mkdir asound                                                        |
    |   sudo cp -r /proc/asound asound                                      |
    |   sudo zip -r asound.zip asound                                       |
    |                                                                       |
    | go to https://github.com/fenrog/supersid/issues                       |
    | Create a new issue,                                                   |
    | add the output of find_als_devices.py,                                |
    | and attach asound.zip.                                                |
    |                                                                       |
    | You may want to use the command line parameter -b/--brute-force       |
    | in order to test a wide range of parameter combinations.              |
    +-----------------------------------------------------------------------+""")

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

    ASOUND_2_ALSAAUDIO_FORMATS = {v: k for k, v in ALSAAUDIO_2_ASOUND_FORMATS.items()}


    class alsaaudio_tester():
        RESULTS = ['OK', 'E_UNKNOWN', 'E_ALSAAUDIO', 'E_OVERRUN', 'E_ZERO_LENGTH', 'E_INVALID_LENGTH', 'E_INVALID_DATA_LENGTH', 'E_RECORDED_ALL_ZEROS', 'F_NOT_IMPLEMENTED']
        def __init__(self):
            self.pcm_devices = alsaaudio.pcms(alsaaudio.PCM_CAPTURE)
            # the numbering of these constants has to match the corresponidng positon within RESULTS
            self.OK = 0
            self.E_UNKNOWN = 1
            self.E_ALSAAUDIO = 2
            self.E_OVERRUN = 3
            self.E_ZERO_LENGTH = 4
            self.E_INVALID_LENGTH = 5
            self.E_INVALID_DATA_LENGTH = 6
            self.E_RECORDED_ALL_ZEROS = 7
            self.F_NOT_IMPLEMENTED = 8

        def test_configuration(self, pcm_device, rate, format, periodsize):
            try:
                channels = 1
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
                    In PCM_NORMAL mode, this function blocks until a full period is available, and then
                    returns a tuple (length,data) where length is the number of frames of captured data,
                    and data is the captured sound frames as a string. The length of the returned data
                    will be periodsize*framesize bytes.

                    In case of an overrun, this function will return a negative size: -EPIPE. This indicates
                    that data was lost, even if the operation itself succeeded. Try using a larger
                    periodsize.
                    """
                    if length < 0:
                        return self.E_OVERRUN, None, None, None
                    if length == 0:
                        return self.E_ZERO_LENGTH, None, None, None
                    if 0 != (length % periodsize):
                        return self.E_INVALID_LENGTH, None, None, None        # expecting an even multiple of periodsize
                    if (length * framesize) != len(data):
                        return self.E_INVALID_DATA_LENGTH, None, None, None   # number of frames multiplied with size of frames must be the size of the buffer
                t_end = time.time()
                t_duration = t_end - t_start

                assert(len(raw_data) >= (framesize * rate))
                asound_format = ALSAAUDIO_2_ASOUND_FORMATS[format]
                if asound_format == 'S16_LE':
                    unpacked_data = array(st_unpack("<%ih" % rate, raw_data[:framesize * rate]))
                elif asound_format == 'S24_3LE':
                    unpacked_data = []
                    for i in range(rate):
                        chunk = raw_data[i*3:i*3+3]
                        unpacked_data.append(st_unpack('<i', chunk + (b'\0' if chunk[2] < 128 else b'\xff'))[0])
                elif asound_format == 'S32_LE':
                    unpacked_data = array(st_unpack("<%ii" % rate, raw_data[:framesize * rate]))
                else:
                    print("\tERROR: format conversion of '{}' is not implemented".format(asound_format))
                    return self.F_NOT_IMPLEMENTED, None, None, None
                assert(len(unpacked_data) == rate)

                if min(unpacked_data) == max(unpacked_data):
                    return self.E_RECORDED_ALL_ZEROS, None, None, None

                NFFT = max(1024, 1024 * rate // 48000)    # NFFT = 1024 for 44100 and 48000, 2048 for 96000, 4096 for 192000 -> the frequency resolution is constant
                Pxx, freqs = mlab_psd(unpacked_data, NFFT, rate)
                m = max(Pxx)
                if m == min(Pxx):
                    peak_freq = None
                else:
                    pos = [i for i, j in enumerate(Pxx) if j == m]
                    peak_freq = freqs[pos]

                return self.OK, unpacked_data, t_duration, peak_freq
            except alsaaudio.ALSAAudioError as e:
                print("\tALSAAudioError {}".format(e))
                return self.E_ALSAAUDIO, None, None, None
            except Exception as e:
                print(type(e), e)
            return self.E_UNKNOWN, None, None, None

        def test(self, interfaces, periodsize, regression):
            tested_pcm_devices = []
            print("audio_sampling_rate, Audio, Card, Format, PeriodSize, regression, result[, duration][, peak freqency]")
            for pcm_device in self.pcm_devices:
                for interface in interfaces:
                    card = interface['card']
                    if card in pcm_device:
                        tested_pcm_devices.append(pcm_device)
                        for rate in interface['rates']:
                            for format in interface['formats']:
                                asound_format = format
                                alsaaudio_format = ASOUND_2_ALSAAUDIO_FORMATS[asound_format]
                                for i in range(regression):
                                    result, data, duration, peak_freq = self.test_configuration(pcm_device, rate, alsaaudio_format, periodsize)
                                    print("{:6d}, alsaaudio, {}, {:7s}, {}, {:2d}, {}{}{}".format(
                                        rate, pcm_device, asound_format, periodsize, i+1, self.RESULTS[result],
                                        "" if duration is None else ', {:.2f} s'.format(duration),
                                        "" if peak_freq is None else ", " + ", ".join('{} Hz'.format(int(f)) for f in peak_freq)))
            print('list of untested devices:')
            pprint(set(self.pcm_devices) - set(tested_pcm_devices))

except ImportError:
    print("ERROR: 'alsaaudio' is not available, on Linux try 'python3 -m pip install alsaaudio'")
    ALSAAUDIO_IS_PRESENT = False


if __name__ == '__main__':
    parser = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter, description="""
Test the audio capturing capability with the python module 'alsaaudio'.
Combinations of card, sampling-rate, format, periodsitze are tested.
Each combination is regression tested as specified by -r/--regression.
The list of tests which will be done can be queried with -l/--list.

Per default the folder /proc/asound is searched for audio cards which are
capable to capture. Their supported sample rates and formats are tested.

This behaviour can be overridden with the -b/--brute-force parameter.
In case of brute force, all 'alsaaudio' PCMs are tested with various
baudrates and formats. Do not use --brute-force unless there is no result
otherwise.

It is recommended to connect a frequency generator to the line in which
is to be tested. Set the frequency to 10000 Hz.
With 41100 samples/sec rate the peak frequency should be 9991 Hz.
With 48k, 96k, 192k samples/s the peak frequency should be 9984 Hz.
The deviation from 10000 depends on the frequency resolution of the FFT.

Some parameter combinations are not suitable at all.
Other combinations yield wrong output (i.e. wrong freuencies measured).
Other combinations deliver unstable results. In on second the measured
freuquency is correct, in the next second it is wrong.

The most valuable output you will get with the command
python3 -u {} 2>&1 | grep OK

Select a combination with properties in this order:
- it yields a duration of 1 s and the expected frequency in each regression
- the highest possible sampling rate
  192000 is better than 96000, which is better than 48000
- a format using highest number of bits
  S32_LE is better than S24_3LE, which is better than S16_LE

The selected parameter combination can be entered in supersid.cfg as follows.
Example output:
192000, alsaaudio, plughw:CARD=Generic,DEV=0, S24_3LE, 1024,  1, OK, 1.01 s, 9984 Hz
192000, alsaaudio, plughw:CARD=Generic,DEV=0, S24_3LE, 1024,  2, OK, 1.01 s, 9984 Hz
192000, alsaaudio, plughw:CARD=Generic,DEV=0, S24_3LE, 1024,  3, OK, 1.01 s, 9984 Hz
192000, alsaaudio, plughw:CARD=Generic,DEV=0, S24_3LE, 1024,  4, OK, 1.01 s, 9984 Hz
192000, alsaaudio, plughw:CARD=Generic,DEV=0, S24_3LE, 1024,  5, OK, 1.01 s, 9984 Hz
192000, alsaaudio, plughw:CARD=Generic,DEV=0, S24_3LE, 1024,  6, OK, 1.01 s, 9984 Hz
192000, alsaaudio, plughw:CARD=Generic,DEV=0, S24_3LE, 1024,  7, OK, 1.01 s, 9984 Hz
192000, alsaaudio, plughw:CARD=Generic,DEV=0, S24_3LE, 1024,  8, OK, 1.01 s, 9984 Hz
192000, alsaaudio, plughw:CARD=Generic,DEV=0, S24_3LE, 1024,  9, OK, 1.01 s, 9984 Hz
192000, alsaaudio, plughw:CARD=Generic,DEV=0, S24_3LE, 1024, 10, OK, 1.01 s, 9984 Hz

supersid.cfg:

[PARAMETERS]
audio_sampling_rate = 192000

[Capture]
Audio = alsaaudio
Card = plughw:CARD=Generic,DEV=0
Format = S24_3LE
PeriodSize = 1024
""".format(__file__))
    parser.add_argument("-b", "--brute-force", help="brute force test all 'alsaaudio' PCMs", action='store_true')
    parser.add_argument("-l", "--list", help="list the parameter combinations and exit", action='store_true')
    parser.add_argument("-p", "--periodsize", help="""periodsize parameter of the PCM interface
default=1024, if the computer runs out of memory,
select smaller numbers like 128, 256, 512, ...""", type=int, default=1024)
    parser.add_argument("-r", "--regression", help="regressions with the same settings, default=10", type=int, default=10)
    parser.add_argument("-t", "--test-dir", help="Not for normal use: prefix for /proc/asound; Used for the test of proc_asound_walker()", default=None)
    args = parser.parse_args()

    if args.list:
        if ALSAAUDIO_IS_PRESENT:
            device_list = alsaaudio.pcms(alsaaudio.PCM_CAPTURE)
            print("List of 'alsaaudio' PCMs:")
            for device in device_list:
                print("\t{}".format(device))
            print()
        else:
            print("ERROR: 'alsaaudio' is not available. Option -l/--list is not fully functional.")

    interfaces = []
    if args.brute_force:
        if ALSAAUDIO_IS_PRESENT:
            device_list = alsaaudio.pcms(alsaaudio.PCM_CAPTURE)
            for device in device_list:
                interfaces.append({
                    'card': device,
                    'rates': DEFAULT_RATES,
                    'formats': DEFAULT_FORMATS,
                    'channels': DEFAULT_CHANNELS,
                })
        else:
            print("ERROR: 'alsaaudio' is not available. Option -b/--brute-force is not available.")
    else:
        if True: #try:
            interfaces = proc_asound_walker(args.test_dir).get_capture_interfaces()
        else: #except Exception as err:
            print("ERROR: {}, {}".format(type(err), err))
            proc_asound_walker(args.test_dir).print_zip()
        print()

    for interface in interfaces:
        print(interface['card'])
        print('\trates:', interface['rates'])
        print('\tformats:', interface['formats'])
        print('\tchannels:', interface['channels'])

    if args.list:
        sys.exit(0)

    print()
    if ALSAAUDIO_IS_PRESENT:
        alsaaudio_tester().test(interfaces, args.periodsize, args.regression)
    else:
        print("ERROR: 'alsaaudio' is not available. Thus the alsaaudio test is not available.")
