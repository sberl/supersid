# find_alsa_devices.py

## Requirements

find_alsa_devices.py can be used in Linux environments.
The python module *alsaaudio* is required to be installed.
Also *alsa-utils* have to be installed.


## Principle

find_alsa_devices.py tests the audio capturing capability.
Combinations of device, sampling-rate, format, periodsize are tested.

Per default 'arecord' is queried for audio cards which are capable to
capture. Their supported sample rates and formats are tested.

It is recommended to connect the line out of each device with it's own
line in. The line out will be used to generate a test tone.
The frequency of the test tone will be 2/3 of the sample frequency.
The captured data of the line in is checked for the peak frequency.
There is a deviation between the peak frequency and the sample frequency.
This is caused by the frequency resolution of the FFT.

-d/--device can be used to limit the test to one device.
-d shall refer to a device with the format "CARD=xxxx".

-t/--test-tone can be used to configure the source of the test tone.
If -d is set and -t is not set, -t will use the same setting as -d.
-t can refer to a device with the format "CARD=xxxx".
-t can also be set as "external" or "external,10000" 
   where the number is the external test frequency. In this case use 
   an external frequency generator set to the configured frequency.

If only -d is given, connect the line out of the device with it's line in.
If -t and -d are given, connect the line out of the -t device with the line in of the -d device.

Each combination is regression tested as specified by -r/--regression.

The list of tests which will be done can be queried with -l/--list.

As kind of a last resort -b/--brute-force can be used.
In case of brute force, all 'alsaaudio' PCMs are tested with various
sampling rates and formats. Do not use --brute-force unless there is no result
otherwise.

-s/--save-wav saves wave files of the one second recordings.

Saving wave files is not meant for everyday use.
This option has been added for analysis and troubleshooting mainly during the development phase.

-v/--verbose produces verbose output mentioning the called external executables and the saved files.


# Use cases

The follwing examples are tested on a Raspberry Pi 400 with "Ubuntu 20.04.3 LTS".
Three extanal USB sound cards are connected:

- Creative Labs Sound Blaster Play!
- Behringer U-Phoria UMC202HD (bcdDevice 1.12; it has been observed that bcdDevice 1.00 is not working)
- VIA USB Dongle


## List devices

Command
```console
    $ python3 -u find_alsa_devices.py -l
```

Example
```example
    Version 20211227
    Config file '../Config/supersid.cfg' read successfully
    List of 'alsaaudio' PCMs:
            default
            sysdefault
            null
            samplerate
            speexrate
            jack
            oss
            pulse
            upmix
            vdownmix
            sysdefault:CARD=Dongle
            front:CARD=Dongle,DEV=0
            surround21:CARD=Dongle,DEV=0
            surround40:CARD=Dongle,DEV=0
            surround41:CARD=Dongle,DEV=0
            surround50:CARD=Dongle,DEV=0
            surround51:CARD=Dongle,DEV=0
            surround71:CARD=Dongle,DEV=0
            iec958:CARD=Dongle,DEV=0
            dmix:CARD=Dongle,DEV=0
            dsnoop:CARD=Dongle,DEV=0
            hw:CARD=Dongle,DEV=0
            plughw:CARD=Dongle,DEV=0
            usbstream:CARD=Dongle
            sysdefault:CARD=U0x41e0x30d3
            front:CARD=U0x41e0x30d3,DEV=0
            surround21:CARD=U0x41e0x30d3,DEV=0
            surround40:CARD=U0x41e0x30d3,DEV=0
            surround41:CARD=U0x41e0x30d3,DEV=0
            surround50:CARD=U0x41e0x30d3,DEV=0
            surround51:CARD=U0x41e0x30d3,DEV=0
            surround71:CARD=U0x41e0x30d3,DEV=0
            iec958:CARD=U0x41e0x30d3,DEV=0
            dmix:CARD=U0x41e0x30d3,DEV=0
            dsnoop:CARD=U0x41e0x30d3,DEV=0
            hw:CARD=U0x41e0x30d3,DEV=0
            plughw:CARD=U0x41e0x30d3,DEV=0
            usbstream:CARD=U0x41e0x30d3
            sysdefault:CARD=U192k
            front:CARD=U192k,DEV=0
            surround21:CARD=U192k,DEV=0
            surround40:CARD=U192k,DEV=0
            surround41:CARD=U192k,DEV=0
            surround50:CARD=U192k,DEV=0
            surround51:CARD=U192k,DEV=0
            surround71:CARD=U192k,DEV=0
            iec958:CARD=U192k,DEV=0
            dmix:CARD=U192k,DEV=0
            dsnoop:CARD=U192k,DEV=0
            hw:CARD=U192k,DEV=0
            plughw:CARD=U192k,DEV=0
            usbstream:CARD=U192k

    CARD=Dongle,DEV=0
            rates: [44100, 48000, 64000, 88200, 96000]
            formats: ['S16_LE', 'S24_3LE']
            channels: 2
    CARD=U0x41e0x30d3,DEV=0
            rates: [44100, 48000]
            formats: ['S16_LE']
            channels: 1
    CARD=U192k,DEV=0
            rates: [44100, 48000, 64000, 88200, 96000, 176400, 192000]
            formats: ['S32_LE']
            channels: 2
```


## Typical usage, identify devices supporting one channel

Connect the line out of each device with the line in of the same device. E.g.:<br />
Connect the line out of U192k to the line in of U192k.<br />
Connect the line out of Dongle to the line in of Dongle.<br />
Connect the line out of U0x41e0x30d3 to the line in of U0x41e0x30d3.<br />

Command
```console
    $ python3 -u find_alsa_devices.py 2>&1
```

Example
```example
    ...

    32 candidates found.
    Prefer candidates with these properties:
    - audio_sampling_rate = highest available value
    - Format = the more bits the better (32 better than 24, 24 better than 16)

    This is the complete list of candidates fulfilling the minimum requirements:
                                    Device  audio_sampling_rate   Format  PeriodSize
    0               sysdefault:CARD=Dongle                48000   S16_LE        1024
    1               sysdefault:CARD=Dongle                48000  S24_3LE        1024
    2             plughw:CARD=Dongle,DEV=0                44100   S16_LE        1024
    3             plughw:CARD=Dongle,DEV=0                44100  S24_3LE        1024
    4             plughw:CARD=Dongle,DEV=0                48000   S16_LE        1024
    5             plughw:CARD=Dongle,DEV=0                48000  S24_3LE        1024
    6             plughw:CARD=Dongle,DEV=0                64000   S16_LE        1024
    7             plughw:CARD=Dongle,DEV=0                64000  S24_3LE        1024
    8             plughw:CARD=Dongle,DEV=0                88200   S16_LE        1024
    9             plughw:CARD=Dongle,DEV=0                88200  S24_3LE        1024
    10            plughw:CARD=Dongle,DEV=0                96000   S16_LE        1024
    11            plughw:CARD=Dongle,DEV=0                96000  S24_3LE        1024
    12        sysdefault:CARD=U0x41e0x30d3                48000   S16_LE        1024
    13       front:CARD=U0x41e0x30d3,DEV=0                44100   S16_LE        1024
    14       front:CARD=U0x41e0x30d3,DEV=0                48000   S16_LE        1024
    15  surround40:CARD=U0x41e0x30d3,DEV=0                44100   S16_LE        1024
    16  surround40:CARD=U0x41e0x30d3,DEV=0                48000   S16_LE        1024
    17      iec958:CARD=U0x41e0x30d3,DEV=0                44100   S16_LE        1024
    18      iec958:CARD=U0x41e0x30d3,DEV=0                48000   S16_LE        1024
    19      dsnoop:CARD=U0x41e0x30d3,DEV=0                48000   S16_LE        1024
    20          hw:CARD=U0x41e0x30d3,DEV=0                44100   S16_LE        1024
    21          hw:CARD=U0x41e0x30d3,DEV=0                48000   S16_LE        1024
    22      plughw:CARD=U0x41e0x30d3,DEV=0                44100   S16_LE        1024
    23      plughw:CARD=U0x41e0x30d3,DEV=0                48000   S16_LE        1024
    24               sysdefault:CARD=U192k                48000   S32_LE        1024
    25             plughw:CARD=U192k,DEV=0                44100   S32_LE        1024
    26             plughw:CARD=U192k,DEV=0                48000   S32_LE        1024
    27             plughw:CARD=U192k,DEV=0                64000   S32_LE        1024
    28             plughw:CARD=U192k,DEV=0                88200   S32_LE        1024
    29             plughw:CARD=U192k,DEV=0                96000   S32_LE        1024
    30             plughw:CARD=U192k,DEV=0               176400   S32_LE        1024
    31             plughw:CARD=U192k,DEV=0               192000   S32_LE        1024

    This is the supersid.cfg setting of the best candidate:
    # candidate 'plughw:CARD=U192k,DEV=0', 192000, S32_LE, 1024
    [PARAMETERS]
    audio_sampling_rate = 192000
    [Capture]
    Audio = alsaaudio
    Device = plughw:CARD=U192k,DEV=0
    Format = S32_LE
    PeriodSize = 1024

    spent 916 seconds
```


## Identify devices supporting two channels

Connect the line out of each device with the line in of the same device. E.g.:<br />
Connect the line out of U192k to the line in of U192k.<br />
Connect the line out of Dongle to the line in of Dongle.<br />
Connect the line out of U0x41e0x30d3 to the line in of U0x41e0x30d3.<br />

Command
```console
    $ python3 -u find_alsa_devices.py -n 2 2>&1
```

Example
```example
    ...

    70 candidates found.
    Prefer candidates with these properties:
    - audio_sampling_rate = highest available value
    - Format = the more bits the better (32 better than 24, 24 better than 16)

    This is the complete list of candidates fulfilling the minimum requirements:
                              Device  audio_sampling_rate   Format  PeriodSize
    0         sysdefault:CARD=Dongle                48000   S16_LE        1024
    1         sysdefault:CARD=Dongle                48000  S24_3LE        1024
    2        front:CARD=Dongle,DEV=0                44100   S16_LE        1024
    3        front:CARD=Dongle,DEV=0                44100  S24_3LE        1024
    4        front:CARD=Dongle,DEV=0                48000   S16_LE        1024
    5        front:CARD=Dongle,DEV=0                48000  S24_3LE        1024
    6        front:CARD=Dongle,DEV=0                96000   S16_LE        1024
    7        front:CARD=Dongle,DEV=0                96000  S24_3LE        1024
    8   surround40:CARD=Dongle,DEV=0                44100   S16_LE        1024
    9   surround40:CARD=Dongle,DEV=0                44100  S24_3LE        1024
    10  surround40:CARD=Dongle,DEV=0                48000   S16_LE        1024
    11  surround40:CARD=Dongle,DEV=0                48000  S24_3LE        1024
    12  surround40:CARD=Dongle,DEV=0                96000   S16_LE        1024
    13  surround40:CARD=Dongle,DEV=0                96000  S24_3LE        1024
    14      iec958:CARD=Dongle,DEV=0                44100   S16_LE        1024
    15      iec958:CARD=Dongle,DEV=0                44100  S24_3LE        1024
    16      iec958:CARD=Dongle,DEV=0                48000   S16_LE        1024
    17      iec958:CARD=Dongle,DEV=0                48000  S24_3LE        1024
    18      iec958:CARD=Dongle,DEV=0                96000   S16_LE        1024
    19      iec958:CARD=Dongle,DEV=0                96000  S24_3LE        1024
    20      dsnoop:CARD=Dongle,DEV=0                48000   S16_LE        1024
    21          hw:CARD=Dongle,DEV=0                44100   S16_LE        1024
    22          hw:CARD=Dongle,DEV=0                44100  S24_3LE        1024
    23          hw:CARD=Dongle,DEV=0                48000   S16_LE        1024
    24          hw:CARD=Dongle,DEV=0                48000  S24_3LE        1024
    25          hw:CARD=Dongle,DEV=0                96000   S16_LE        1024
    26          hw:CARD=Dongle,DEV=0                96000  S24_3LE        1024
    27      plughw:CARD=Dongle,DEV=0                44100   S16_LE        1024
    28      plughw:CARD=Dongle,DEV=0                44100  S24_3LE        1024
    29      plughw:CARD=Dongle,DEV=0                48000   S16_LE        1024
    30      plughw:CARD=Dongle,DEV=0                48000  S24_3LE        1024
    31      plughw:CARD=Dongle,DEV=0                64000   S16_LE        1024
    32      plughw:CARD=Dongle,DEV=0                64000  S24_3LE        1024
    33      plughw:CARD=Dongle,DEV=0                88200   S16_LE        1024
    34      plughw:CARD=Dongle,DEV=0                88200  S24_3LE        1024
    35      plughw:CARD=Dongle,DEV=0                96000   S16_LE        1024
    36      plughw:CARD=Dongle,DEV=0                96000  S24_3LE        1024
    37         sysdefault:CARD=U192k                48000   S32_LE        1024
    38        front:CARD=U192k,DEV=0                44100   S32_LE        1024
    39        front:CARD=U192k,DEV=0                48000   S32_LE        1024
    40        front:CARD=U192k,DEV=0                88200   S32_LE        1024
    41        front:CARD=U192k,DEV=0                96000   S32_LE        1024
    42        front:CARD=U192k,DEV=0               176400   S32_LE        1024
    43        front:CARD=U192k,DEV=0               192000   S32_LE        1024
    44   surround40:CARD=U192k,DEV=0                44100   S32_LE        1024
    45   surround40:CARD=U192k,DEV=0                48000   S32_LE        1024
    46   surround40:CARD=U192k,DEV=0                88200   S32_LE        1024
    47   surround40:CARD=U192k,DEV=0                96000   S32_LE        1024
    48   surround40:CARD=U192k,DEV=0               176400   S32_LE        1024
    49   surround40:CARD=U192k,DEV=0               192000   S32_LE        1024
    50       iec958:CARD=U192k,DEV=0                44100   S32_LE        1024
    51       iec958:CARD=U192k,DEV=0                48000   S32_LE        1024
    52       iec958:CARD=U192k,DEV=0                88200   S32_LE        1024
    53       iec958:CARD=U192k,DEV=0                96000   S32_LE        1024
    54       iec958:CARD=U192k,DEV=0               176400   S32_LE        1024
    55       iec958:CARD=U192k,DEV=0               192000   S32_LE        1024
    56       dsnoop:CARD=U192k,DEV=0                48000   S32_LE        1024
    57           hw:CARD=U192k,DEV=0                44100   S32_LE        1024
    58           hw:CARD=U192k,DEV=0                48000   S32_LE        1024
    59           hw:CARD=U192k,DEV=0                88200   S32_LE        1024
    60           hw:CARD=U192k,DEV=0                96000   S32_LE        1024
    61           hw:CARD=U192k,DEV=0               176400   S32_LE        1024
    62           hw:CARD=U192k,DEV=0               192000   S32_LE        1024
    63       plughw:CARD=U192k,DEV=0                44100   S32_LE        1024
    64       plughw:CARD=U192k,DEV=0                48000   S32_LE        1024
    65       plughw:CARD=U192k,DEV=0                64000   S32_LE        1024
    66       plughw:CARD=U192k,DEV=0                88200   S32_LE        1024
    67       plughw:CARD=U192k,DEV=0                96000   S32_LE        1024
    68       plughw:CARD=U192k,DEV=0               176400   S32_LE        1024
    69       plughw:CARD=U192k,DEV=0               192000   S32_LE        1024

    These are the supersid.cfg settings of the best candidates:
    # candidate 'front:CARD=U192k,DEV=0', 192000, S32_LE, 1024
    [PARAMETERS]
    audio_sampling_rate = 192000
    [Capture]
    Audio = alsaaudio
    Device = front:CARD=U192k,DEV=0
    Format = S32_LE
    PeriodSize = 1024

    # candidate 'surround40:CARD=U192k,DEV=0', 192000, S32_LE, 1024
    [PARAMETERS]
    audio_sampling_rate = 192000
    [Capture]
    Audio = alsaaudio
    Device = surround40:CARD=U192k,DEV=0
    Format = S32_LE
    PeriodSize = 1024

    # candidate 'iec958:CARD=U192k,DEV=0', 192000, S32_LE, 1024
    [PARAMETERS]
    audio_sampling_rate = 192000
    [Capture]
    Audio = alsaaudio
    Device = iec958:CARD=U192k,DEV=0
    Format = S32_LE
    PeriodSize = 1024

    # candidate 'hw:CARD=U192k,DEV=0', 192000, S32_LE, 1024
    [PARAMETERS]
    audio_sampling_rate = 192000
    [Capture]
    Audio = alsaaudio
    Device = hw:CARD=U192k,DEV=0
    Format = S32_LE
    PeriodSize = 1024

    # candidate 'plughw:CARD=U192k,DEV=0', 192000, S32_LE, 1024
    [PARAMETERS]
    audio_sampling_rate = 192000
    [Capture]
    Audio = alsaaudio
    Device = plughw:CARD=U192k,DEV=0
    Format = S32_LE
    PeriodSize = 1024

    spent 2026 seconds
```


## Test a single device with loopback

Connect the line out of U192k to the line in of U192k.<br />
-d can be one of alsaaudio PCMs or one of the devices, optionally without ',DEV=0'.

Examples:
- -d plughw:CARD=U192k,DEV=0
- -d CARD=U192k,DEV=0
- -d CARD=U192k

Command
```console
    $ python3 -u find_alsa_devices.py -d plughw:CARD=U192k,DEV=0
```

Example
```example
    ...

    7 candidates found.
    Prefer candidates with these properties:
    - audio_sampling_rate = highest available value
    - Format = the more bits the better (32 better than 24, 24 better than 16)

    This is the complete list of candidates fulfilling the minimum requirements:
                        Device  audio_sampling_rate  Format  PeriodSize
    0  plughw:CARD=U192k,DEV=0                44100  S32_LE        1024
    1  plughw:CARD=U192k,DEV=0                48000  S32_LE        1024
    2  plughw:CARD=U192k,DEV=0                64000  S32_LE        1024
    3  plughw:CARD=U192k,DEV=0                88200  S32_LE        1024
    4  plughw:CARD=U192k,DEV=0                96000  S32_LE        1024
    5  plughw:CARD=U192k,DEV=0               176400  S32_LE        1024
    6  plughw:CARD=U192k,DEV=0               192000  S32_LE        1024

    This is the supersid.cfg setting of the best candidate:
    # candidate 'plughw:CARD=U192k,DEV=0', 192000, S32_LE, 1024
    [PARAMETERS]
    audio_sampling_rate = 192000
    [Capture]
    Audio = alsaaudio
    Device = plughw:CARD=U192k,DEV=0
    Format = S32_LE
    PeriodSize = 1024

    spent 96 seconds
```


## Test a single device with loopback and save wave files of the recordings, be verbose

Connect the line out of U0x41e0x30d3 to the line in of U0x41e0x30d3.

Command
```console
    $ python3 -u find_alsa_devices.py -d plughw:CARD=U0x41e0x30d3 -s -v
```

Example
```example
    ...

    2 candidates found.
    Prefer candidates with these properties:
    - audio_sampling_rate = highest available value
    - Format = the more bits the better (32 better than 24, 24 better than 16)

    This is the complete list of candidates fulfilling the minimum requirements:
                               Device  audio_sampling_rate  Format  PeriodSize
    0  plughw:CARD=U0x41e0x30d3,DEV=0                44100  S16_LE        1024
    1  plughw:CARD=U0x41e0x30d3,DEV=0                48000  S16_LE        1024

    This is the supersid.cfg setting of the best candidate:
    # candidate 'plughw:CARD=U0x41e0x30d3,DEV=0', 48000, S16_LE, 1024
    [PARAMETERS]
    audio_sampling_rate = 48000
    [Capture]
    Audio = alsaaudio
    Device = plughw:CARD=U0x41e0x30d3,DEV=0
    Format = S16_LE
    PeriodSize = 1024

    spent 29 seconds
```

Generated files
```console
    $ ls ../Data/*.wav
    ../Data/fad_plughw.CARD.U0x41e0x30d3.DEV.0_44100_S16_LE_1024_0.wav
    ../Data/fad_plughw.CARD.U0x41e0x30d3.DEV.0_44100_S16_LE_1024_1.wav
    ../Data/fad_plughw.CARD.U0x41e0x30d3.DEV.0_44100_S16_LE_1024_2.wav
    ../Data/fad_plughw.CARD.U0x41e0x30d3.DEV.0_44100_S16_LE_1024_3.wav
    ../Data/fad_plughw.CARD.U0x41e0x30d3.DEV.0_44100_S16_LE_1024_4.wav
    ../Data/fad_plughw.CARD.U0x41e0x30d3.DEV.0_44100_S16_LE_1024_5.wav
    ../Data/fad_plughw.CARD.U0x41e0x30d3.DEV.0_44100_S16_LE_1024_6.wav
    ../Data/fad_plughw.CARD.U0x41e0x30d3.DEV.0_44100_S16_LE_1024_7.wav
    ../Data/fad_plughw.CARD.U0x41e0x30d3.DEV.0_44100_S16_LE_1024_8.wav
    ../Data/fad_plughw.CARD.U0x41e0x30d3.DEV.0_44100_S16_LE_1024_9.wav
    ../Data/fad_plughw.CARD.U0x41e0x30d3.DEV.0_48000_S16_LE_1024_0.wav
    ../Data/fad_plughw.CARD.U0x41e0x30d3.DEV.0_48000_S16_LE_1024_1.wav
    ../Data/fad_plughw.CARD.U0x41e0x30d3.DEV.0_48000_S16_LE_1024_2.wav
    ../Data/fad_plughw.CARD.U0x41e0x30d3.DEV.0_48000_S16_LE_1024_3.wav
    ../Data/fad_plughw.CARD.U0x41e0x30d3.DEV.0_48000_S16_LE_1024_4.wav
    ../Data/fad_plughw.CARD.U0x41e0x30d3.DEV.0_48000_S16_LE_1024_5.wav
    ../Data/fad_plughw.CARD.U0x41e0x30d3.DEV.0_48000_S16_LE_1024_6.wav
    ../Data/fad_plughw.CARD.U0x41e0x30d3.DEV.0_48000_S16_LE_1024_7.wav
    ../Data/fad_plughw.CARD.U0x41e0x30d3.DEV.0_48000_S16_LE_1024_8.wav
    ../Data/fad_plughw.CARD.U0x41e0x30d3.DEV.0_48000_S16_LE_1024_9.wav
```


## Test a single device with another device producing the test tone

Connect the line out of U192k to the line in of Dongle.

Command
```console
    $ python3 -u find_alsa_devices.py -d CARD=Dongle -t CARD=U192k 
```

Example
```example
    ...

    12 candidates found.
    Prefer candidates with these properties:
    - audio_sampling_rate = highest available value
    - Format = the more bits the better (32 better than 24, 24 better than 16)

    This is the complete list of candidates fulfilling the minimum requirements:
                          Device  audio_sampling_rate   Format  PeriodSize
    0     sysdefault:CARD=Dongle                48000   S16_LE        1024
    1     sysdefault:CARD=Dongle                48000  S24_3LE        1024
    2   plughw:CARD=Dongle,DEV=0                44100   S16_LE        1024
    3   plughw:CARD=Dongle,DEV=0                44100  S24_3LE        1024
    4   plughw:CARD=Dongle,DEV=0                48000   S16_LE        1024
    5   plughw:CARD=Dongle,DEV=0                48000  S24_3LE        1024
    6   plughw:CARD=Dongle,DEV=0                64000   S16_LE        1024
    7   plughw:CARD=Dongle,DEV=0                64000  S24_3LE        1024
    8   plughw:CARD=Dongle,DEV=0                88200   S16_LE        1024
    9   plughw:CARD=Dongle,DEV=0                88200  S24_3LE        1024
    10  plughw:CARD=Dongle,DEV=0                96000   S16_LE        1024
    11  plughw:CARD=Dongle,DEV=0                96000  S24_3LE        1024

    This is the supersid.cfg setting of the best candidate:
    # candidate 'plughw:CARD=Dongle,DEV=0', 96000, S24_3LE, 1024
    [PARAMETERS]
    audio_sampling_rate = 96000
    [Capture]
    Audio = alsaaudio
    Device = plughw:CARD=Dongle,DEV=0
    Format = S24_3LE
    PeriodSize = 1024

    spent 350 seconds
```


## Test a single device with an external frequency generator

Connect the output of the frequency generator with 10000 Hz to the line in of U192k.

Command
```console
    $ python3 -u find_alsa_devices.py -d CARD=U192k -t external,10000
```

Example
```example
    ...

    10 candidates found.
    Prefer candidates with these properties:
    - audio_sampling_rate = highest available value
    - Format = the more bits the better (32 better than 24, 24 better than 16)

    This is the complete list of candidates fulfilling the minimum requirements:
                        Device  audio_sampling_rate  Format  PeriodSize
    0    sysdefault:CARD=U192k                48000  S32_LE        1024
    1    sysdefault:CARD=U192k                96000  S32_LE        1024
    2    sysdefault:CARD=U192k               192000  S32_LE        1024
    3  plughw:CARD=U192k,DEV=0                44100  S32_LE        1024
    4  plughw:CARD=U192k,DEV=0                48000  S32_LE        1024
    5  plughw:CARD=U192k,DEV=0                64000  S32_LE        1024
    6  plughw:CARD=U192k,DEV=0                88200  S32_LE        1024
    7  plughw:CARD=U192k,DEV=0                96000  S32_LE        1024
    8  plughw:CARD=U192k,DEV=0               176400  S32_LE        1024
    9  plughw:CARD=U192k,DEV=0               192000  S32_LE        1024

    These are the supersid.cfg settings of the best candidates:
    # candidate 'sysdefault:CARD=U192k', 192000, S32_LE, 1024
    [PARAMETERS]
    audio_sampling_rate = 192000
    [Capture]
    Audio = alsaaudio
    Device = sysdefault:CARD=U192k
    Format = S32_LE
    PeriodSize = 1024

    # candidate 'plughw:CARD=U192k,DEV=0', 192000, S32_LE, 1024
    [PARAMETERS]
    audio_sampling_rate = 192000
    [Capture]
    Audio = alsaaudio
    Device = plughw:CARD=U192k,DEV=0
    Format = S32_LE
    PeriodSize = 1024

    spent 127 seconds
```


## List brute force devices

Command
```console
    $ python3 -u find_alsa_devices.py -l -b
```

Example
```example
    Version 20211227
    Config file '../Config/supersid.cfg' read successfully
    List of 'alsaaudio' PCMs:
            default
            sysdefault
            null
            samplerate
            speexrate
            jack
            oss
            pulse
            upmix
            vdownmix
            sysdefault:CARD=Dongle
            front:CARD=Dongle,DEV=0
            surround21:CARD=Dongle,DEV=0
            surround40:CARD=Dongle,DEV=0
            surround41:CARD=Dongle,DEV=0
            surround50:CARD=Dongle,DEV=0
            surround51:CARD=Dongle,DEV=0
            surround71:CARD=Dongle,DEV=0
            iec958:CARD=Dongle,DEV=0
            dmix:CARD=Dongle,DEV=0
            dsnoop:CARD=Dongle,DEV=0
            hw:CARD=Dongle,DEV=0
            plughw:CARD=Dongle,DEV=0
            usbstream:CARD=Dongle
            sysdefault:CARD=U0x41e0x30d3
            front:CARD=U0x41e0x30d3,DEV=0
            surround21:CARD=U0x41e0x30d3,DEV=0
            surround40:CARD=U0x41e0x30d3,DEV=0
            surround41:CARD=U0x41e0x30d3,DEV=0
            surround50:CARD=U0x41e0x30d3,DEV=0
            surround51:CARD=U0x41e0x30d3,DEV=0
            surround71:CARD=U0x41e0x30d3,DEV=0
            iec958:CARD=U0x41e0x30d3,DEV=0
            dmix:CARD=U0x41e0x30d3,DEV=0
            dsnoop:CARD=U0x41e0x30d3,DEV=0
            hw:CARD=U0x41e0x30d3,DEV=0
            plughw:CARD=U0x41e0x30d3,DEV=0
            usbstream:CARD=U0x41e0x30d3
            sysdefault:CARD=U192k
            front:CARD=U192k,DEV=0
            surround21:CARD=U192k,DEV=0
            surround40:CARD=U192k,DEV=0
            surround41:CARD=U192k,DEV=0
            surround50:CARD=U192k,DEV=0
            surround51:CARD=U192k,DEV=0
            surround71:CARD=U192k,DEV=0
            iec958:CARD=U192k,DEV=0
            dmix:CARD=U192k,DEV=0
            dsnoop:CARD=U192k,DEV=0
            hw:CARD=U192k,DEV=0
            plughw:CARD=U192k,DEV=0
            usbstream:CARD=U192k

    default
            rates: [44100, 48000, 96000, 192000]
            formats: ['S16_LE', 'S24_3LE', 'S32_LE']
            channels: 1
    sysdefault
            rates: [44100, 48000, 96000, 192000]
            formats: ['S16_LE', 'S24_3LE', 'S32_LE']
            channels: 1
    null
            rates: [44100, 48000, 96000, 192000]
            formats: ['S16_LE', 'S24_3LE', 'S32_LE']
            channels: 1
    samplerate
            rates: [44100, 48000, 96000, 192000]
            formats: ['S16_LE', 'S24_3LE', 'S32_LE']
            channels: 1
    speexrate
            rates: [44100, 48000, 96000, 192000]
            formats: ['S16_LE', 'S24_3LE', 'S32_LE']
            channels: 1
    jack
            rates: [44100, 48000, 96000, 192000]
            formats: ['S16_LE', 'S24_3LE', 'S32_LE']
            channels: 1
    oss
            rates: [44100, 48000, 96000, 192000]
            formats: ['S16_LE', 'S24_3LE', 'S32_LE']
            channels: 1
    pulse
            rates: [44100, 48000, 96000, 192000]
            formats: ['S16_LE', 'S24_3LE', 'S32_LE']
            channels: 1
    upmix
            rates: [44100, 48000, 96000, 192000]
            formats: ['S16_LE', 'S24_3LE', 'S32_LE']
            channels: 1
    vdownmix
            rates: [44100, 48000, 96000, 192000]
            formats: ['S16_LE', 'S24_3LE', 'S32_LE']
            channels: 1
    sysdefault:CARD=Dongle
            rates: [44100, 48000, 96000, 192000]
            formats: ['S16_LE', 'S24_3LE', 'S32_LE']
            channels: 1
    front:CARD=Dongle,DEV=0
            rates: [44100, 48000, 96000, 192000]
            formats: ['S16_LE', 'S24_3LE', 'S32_LE']
            channels: 1
    surround21:CARD=Dongle,DEV=0
            rates: [44100, 48000, 96000, 192000]
            formats: ['S16_LE', 'S24_3LE', 'S32_LE']
            channels: 1
    surround40:CARD=Dongle,DEV=0
            rates: [44100, 48000, 96000, 192000]
            formats: ['S16_LE', 'S24_3LE', 'S32_LE']
            channels: 1
    surround41:CARD=Dongle,DEV=0
            rates: [44100, 48000, 96000, 192000]
            formats: ['S16_LE', 'S24_3LE', 'S32_LE']
            channels: 1
    surround50:CARD=Dongle,DEV=0
            rates: [44100, 48000, 96000, 192000]
            formats: ['S16_LE', 'S24_3LE', 'S32_LE']
            channels: 1
    surround51:CARD=Dongle,DEV=0
            rates: [44100, 48000, 96000, 192000]
            formats: ['S16_LE', 'S24_3LE', 'S32_LE']
            channels: 1
    surround71:CARD=Dongle,DEV=0
            rates: [44100, 48000, 96000, 192000]
            formats: ['S16_LE', 'S24_3LE', 'S32_LE']
            channels: 1
    iec958:CARD=Dongle,DEV=0
            rates: [44100, 48000, 96000, 192000]
            formats: ['S16_LE', 'S24_3LE', 'S32_LE']
            channels: 1
    dmix:CARD=Dongle,DEV=0
            rates: [44100, 48000, 96000, 192000]
            formats: ['S16_LE', 'S24_3LE', 'S32_LE']
            channels: 1
    dsnoop:CARD=Dongle,DEV=0
            rates: [44100, 48000, 96000, 192000]
            formats: ['S16_LE', 'S24_3LE', 'S32_LE']
            channels: 1
    hw:CARD=Dongle,DEV=0
            rates: [44100, 48000, 96000, 192000]
            formats: ['S16_LE', 'S24_3LE', 'S32_LE']
            channels: 1
    plughw:CARD=Dongle,DEV=0
            rates: [44100, 48000, 96000, 192000]
            formats: ['S16_LE', 'S24_3LE', 'S32_LE']
            channels: 1
    usbstream:CARD=Dongle
            rates: [44100, 48000, 96000, 192000]
            formats: ['S16_LE', 'S24_3LE', 'S32_LE']
            channels: 1
    sysdefault:CARD=U0x41e0x30d3
            rates: [44100, 48000, 96000, 192000]
            formats: ['S16_LE', 'S24_3LE', 'S32_LE']
            channels: 1
    front:CARD=U0x41e0x30d3,DEV=0
            rates: [44100, 48000, 96000, 192000]
            formats: ['S16_LE', 'S24_3LE', 'S32_LE']
            channels: 1
    surround21:CARD=U0x41e0x30d3,DEV=0
            rates: [44100, 48000, 96000, 192000]
            formats: ['S16_LE', 'S24_3LE', 'S32_LE']
            channels: 1
    surround40:CARD=U0x41e0x30d3,DEV=0
            rates: [44100, 48000, 96000, 192000]
            formats: ['S16_LE', 'S24_3LE', 'S32_LE']
            channels: 1
    surround41:CARD=U0x41e0x30d3,DEV=0
            rates: [44100, 48000, 96000, 192000]
            formats: ['S16_LE', 'S24_3LE', 'S32_LE']
            channels: 1
    surround50:CARD=U0x41e0x30d3,DEV=0
            rates: [44100, 48000, 96000, 192000]
            formats: ['S16_LE', 'S24_3LE', 'S32_LE']
            channels: 1
    surround51:CARD=U0x41e0x30d3,DEV=0
            rates: [44100, 48000, 96000, 192000]
            formats: ['S16_LE', 'S24_3LE', 'S32_LE']
            channels: 1
    surround71:CARD=U0x41e0x30d3,DEV=0
            rates: [44100, 48000, 96000, 192000]
            formats: ['S16_LE', 'S24_3LE', 'S32_LE']
            channels: 1
    iec958:CARD=U0x41e0x30d3,DEV=0
            rates: [44100, 48000, 96000, 192000]
            formats: ['S16_LE', 'S24_3LE', 'S32_LE']
            channels: 1
    dmix:CARD=U0x41e0x30d3,DEV=0
            rates: [44100, 48000, 96000, 192000]
            formats: ['S16_LE', 'S24_3LE', 'S32_LE']
            channels: 1
    dsnoop:CARD=U0x41e0x30d3,DEV=0
            rates: [44100, 48000, 96000, 192000]
            formats: ['S16_LE', 'S24_3LE', 'S32_LE']
            channels: 1
    hw:CARD=U0x41e0x30d3,DEV=0
            rates: [44100, 48000, 96000, 192000]
            formats: ['S16_LE', 'S24_3LE', 'S32_LE']
            channels: 1
    plughw:CARD=U0x41e0x30d3,DEV=0
            rates: [44100, 48000, 96000, 192000]
            formats: ['S16_LE', 'S24_3LE', 'S32_LE']
            channels: 1
    usbstream:CARD=U0x41e0x30d3
            rates: [44100, 48000, 96000, 192000]
            formats: ['S16_LE', 'S24_3LE', 'S32_LE']
            channels: 1
    sysdefault:CARD=U192k
            rates: [44100, 48000, 96000, 192000]
            formats: ['S16_LE', 'S24_3LE', 'S32_LE']
            channels: 1
    front:CARD=U192k,DEV=0
            rates: [44100, 48000, 96000, 192000]
            formats: ['S16_LE', 'S24_3LE', 'S32_LE']
            channels: 1
    surround21:CARD=U192k,DEV=0
            rates: [44100, 48000, 96000, 192000]
            formats: ['S16_LE', 'S24_3LE', 'S32_LE']
            channels: 1
    surround40:CARD=U192k,DEV=0
            rates: [44100, 48000, 96000, 192000]
            formats: ['S16_LE', 'S24_3LE', 'S32_LE']
            channels: 1
    surround41:CARD=U192k,DEV=0
            rates: [44100, 48000, 96000, 192000]
            formats: ['S16_LE', 'S24_3LE', 'S32_LE']
            channels: 1
    surround50:CARD=U192k,DEV=0
            rates: [44100, 48000, 96000, 192000]
            formats: ['S16_LE', 'S24_3LE', 'S32_LE']
            channels: 1
    surround51:CARD=U192k,DEV=0
            rates: [44100, 48000, 96000, 192000]
            formats: ['S16_LE', 'S24_3LE', 'S32_LE']
            channels: 1
    surround71:CARD=U192k,DEV=0
            rates: [44100, 48000, 96000, 192000]
            formats: ['S16_LE', 'S24_3LE', 'S32_LE']
            channels: 1
    iec958:CARD=U192k,DEV=0
            rates: [44100, 48000, 96000, 192000]
            formats: ['S16_LE', 'S24_3LE', 'S32_LE']
            channels: 1
    dmix:CARD=U192k,DEV=0
            rates: [44100, 48000, 96000, 192000]
            formats: ['S16_LE', 'S24_3LE', 'S32_LE']
            channels: 1
    dsnoop:CARD=U192k,DEV=0
            rates: [44100, 48000, 96000, 192000]
            formats: ['S16_LE', 'S24_3LE', 'S32_LE']
            channels: 1
    hw:CARD=U192k,DEV=0
            rates: [44100, 48000, 96000, 192000]
            formats: ['S16_LE', 'S24_3LE', 'S32_LE']
            channels: 1
    plughw:CARD=U192k,DEV=0
            rates: [44100, 48000, 96000, 192000]
            formats: ['S16_LE', 'S24_3LE', 'S32_LE']
            channels: 1
    usbstream:CARD=U192k
            rates: [44100, 48000, 96000, 192000]
            formats: ['S16_LE', 'S24_3LE', 'S32_LE']
            channels: 1
```


## Brute force, no regression

Connect the line out of each device with the line in of the same device. E.g.:<br />
Connect the line out of U192k to the line in of U192k.<br />
Connect the line out of Dongle to the line in of Dongle.<br />
Connect the line out of U0x41e0x30d3 to the line in of U0x41e0x30d3.<br />

Caution: The likelyhood of false positives is high.<br />
In the example below<br />
'front:CARD=Dongle,DEV=0' and others are reported to support 32 bit samples but the HW supports just 16 and 24 bit.<br />
'plughw:CARD=Dongle,DEV=0' is reported to support 16, 24 and 32 bit samples but the HW supports just 16 and 24 bit.<br />
'plughw:CARD=U0x41e0x30d3,DEV=0' is reported to support 16, 24 and 32 bit samples but there is just a 16 bit ADC in the HW.<br />
The 'improved' capabilities are not real. They are present due to software conversions in the ALSA infrastructure.<br />
Avoid using the -b/--brute-force option unless there is no other solution.<br />
Check whether the results are plausible in the comparison with the device manual.

Command
```console
    $ python3 -u find_alsa_devices.py -b -r1 2>&1
```

Example
```example
    ...

    53 candidates found.
    Prefer candidates with these properties:
    - audio_sampling_rate = highest available value
    - Format = the more bits the better (32 better than 24, 24 better than 16)

    This is the complete list of candidates fulfilling the minimum requirements:
                                    Device  audio_sampling_rate   Format  PeriodSize
    0                              default                44100   S16_LE        1024
    1                              default                44100  S24_3LE        1024
    2                              default                44100   S32_LE        1024
    3                              default                48000   S16_LE        1024
    4                              default                48000  S24_3LE        1024
    5                              default                48000   S32_LE        1024
    6              front:CARD=Dongle,DEV=0                44100   S32_LE        1024
    7              front:CARD=Dongle,DEV=0                48000   S32_LE        1024
    8              front:CARD=Dongle,DEV=0                96000   S32_LE        1024
    9         surround40:CARD=Dongle,DEV=0                44100   S32_LE        1024
    10        surround40:CARD=Dongle,DEV=0                48000   S32_LE        1024
    11        surround40:CARD=Dongle,DEV=0                96000   S32_LE        1024
    12            iec958:CARD=Dongle,DEV=0                44100   S32_LE        1024
    13            iec958:CARD=Dongle,DEV=0                48000   S32_LE        1024
    14            iec958:CARD=Dongle,DEV=0                96000   S32_LE        1024
    15                hw:CARD=Dongle,DEV=0                44100   S32_LE        1024
    16                hw:CARD=Dongle,DEV=0                48000   S32_LE        1024
    17                hw:CARD=Dongle,DEV=0                96000   S32_LE        1024
    18            plughw:CARD=Dongle,DEV=0                44100   S16_LE        1024
    19            plughw:CARD=Dongle,DEV=0                44100  S24_3LE        1024
    20            plughw:CARD=Dongle,DEV=0                44100   S32_LE        1024
    21            plughw:CARD=Dongle,DEV=0                48000   S16_LE        1024
    22            plughw:CARD=Dongle,DEV=0                48000  S24_3LE        1024
    23            plughw:CARD=Dongle,DEV=0                48000   S32_LE        1024
    24            plughw:CARD=Dongle,DEV=0                96000   S16_LE        1024
    25            plughw:CARD=Dongle,DEV=0                96000  S24_3LE        1024
    26            plughw:CARD=Dongle,DEV=0                96000   S32_LE        1024
    27       front:CARD=U0x41e0x30d3,DEV=0                44100   S16_LE        1024
    28       front:CARD=U0x41e0x30d3,DEV=0                48000   S16_LE        1024
    29  surround40:CARD=U0x41e0x30d3,DEV=0                44100   S16_LE        1024
    30  surround40:CARD=U0x41e0x30d3,DEV=0                48000   S16_LE        1024
    31      iec958:CARD=U0x41e0x30d3,DEV=0                44100   S16_LE        1024
    32      iec958:CARD=U0x41e0x30d3,DEV=0                48000   S16_LE        1024
    33          hw:CARD=U0x41e0x30d3,DEV=0                44100   S16_LE        1024
    34          hw:CARD=U0x41e0x30d3,DEV=0                48000   S16_LE        1024
    35      plughw:CARD=U0x41e0x30d3,DEV=0                44100   S16_LE        1024
    36      plughw:CARD=U0x41e0x30d3,DEV=0                44100  S24_3LE        1024
    37      plughw:CARD=U0x41e0x30d3,DEV=0                44100   S32_LE        1024
    38      plughw:CARD=U0x41e0x30d3,DEV=0                48000   S16_LE        1024
    39      plughw:CARD=U0x41e0x30d3,DEV=0                48000  S24_3LE        1024
    40      plughw:CARD=U0x41e0x30d3,DEV=0                48000   S32_LE        1024
    41             plughw:CARD=U192k,DEV=0                44100   S16_LE        1024
    42             plughw:CARD=U192k,DEV=0                44100  S24_3LE        1024
    43             plughw:CARD=U192k,DEV=0                44100   S32_LE        1024
    44             plughw:CARD=U192k,DEV=0                48000   S16_LE        1024
    45             plughw:CARD=U192k,DEV=0                48000  S24_3LE        1024
    46             plughw:CARD=U192k,DEV=0                48000   S32_LE        1024
    47             plughw:CARD=U192k,DEV=0                96000   S16_LE        1024
    48             plughw:CARD=U192k,DEV=0                96000  S24_3LE        1024
    49             plughw:CARD=U192k,DEV=0                96000   S32_LE        1024
    50             plughw:CARD=U192k,DEV=0               192000   S16_LE        1024
    51             plughw:CARD=U192k,DEV=0               192000  S24_3LE        1024
    52             plughw:CARD=U192k,DEV=0               192000   S32_LE        1024

    This is the supersid.cfg setting of the best candidate:
    # candidate 'plughw:CARD=U192k,DEV=0', 192000, S32_LE, 1024
    [PARAMETERS]
    audio_sampling_rate = 192000
    [Capture]
    Audio = alsaaudio
    Device = plughw:CARD=U192k,DEV=0
    Format = S32_LE
    PeriodSize = 1024

    spent 436 seconds
```
