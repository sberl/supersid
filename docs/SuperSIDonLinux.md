# SuperSID on Linux (Ubuntu Server 20.04.3 LTS)

This has been tested on

- Raspberry Pi 400 4GB
- Lenovo PC

## Preparation

[Set up your Raspberry Pi](https://www.raspberrypi.com/documentation/computers/getting-started.html#setting-up-your-raspberry-pi) with the image **UBUNTU SERVER 20.04.3 LTS (RPI 3/4/400)** *64 bit server OS with long-term support for arm64 architectures*.
Boot on the new micro-SD card, follow normal process for any fresh system install. Connect to the internet.

Install the x-server.
```console
    $ sudo apt install xinit
```
Reboot. X will start.
Do the language setup and further required settings like WiFi, language, keyboard layout, time zone, ...
Verify in the settings your sound card is set as input and output device.

Execute the classic:
```console
    $ sudo apt-get update
    $ sudo apt-get upgrade
```


## 1) Get the latest supersid software

Get the source from GitHub.com

```console
    $ cd ~
    $ git clone https://github.com/sberl/supersid.git
```

To update (pull) to the latest version, do:
```console
    $ cd ~/supersid
    $ git pull
```


## 2) Extra software

Time synchro over the Internet:
```console
    $ sudo apt-get install ntpdate ntp
```
Follow the tutorial [Raspberry Pi sync date and time](https://victorhurdugaci.com/raspberry-pi-sync-date-and-time)

Optional: Virtualenv management for Python:
```console
    $ sudo apt-get install mkvirtualenv
```

Numpy also requires a special package (for opening `shared object (.so)` files):
```console
    $ sudo apt-get install libatlas-base-dev
```


## 3) Installing SuperSID

### 3.1) optional virtual environment

This step is optional. Creating your own environment allows to install libraries in all freedom,
without `sudo` and ensure you have a coherent and working set of libraries (sound card).
If your Raspi is dedicated to SuperSID then you can skip this step and install all globally.

From /home/pi:
```console
    $ cd ~/supersid
    $ mkvirtualenv -p /usr/bin/python3 supersid
    $ workon supersid
    $ toggleglobalsitepackages
```

Your prompt should now start with '(supersid)'

This also ensures that we run in Python 3.7.3 as per current configuration.


### 3.2) Global or local installation

This Raspi 3 is dedicated to SuperSid or you do not plan to mix various libraries: install at system level all the libraries.
You can do so exactly like you would do in linux, for an local installation inside the virtual environement by first executing 'workon supersid'.


```console
    $ sudo apt-get install python3-matplotlib
    $ sudo apt-get install python3-pip
    $ sudo apt-get install libasound2-dev
    $ sudo apt-get install python3-numpy
    $ sudo apt-get install python3-pandas
    $ cd ~/supersid
    $ pip3 install -r requirements.txt
```

Optional and not required. Install when you want to test additonal audio libraries:

```console
    $ sudo apt install libportaudio2
    $ pip3 install sounddevice
    $ sudo apt-get install python3-pyaudio
```


## 4) Optional: Build and install wxPython

Build and install wxPython only if you really want to have wxPython, e.g. to test the scripts with 'viewer=wx' with Ubuntu 20.04.
The installation is time consuming.

This guide is an adapted version of [wxPython Python 3 Ubuntu 20.04 Installation](https://tutorialforlinux.com/2020/03/15/step-by-step-wxpython-python-3-ubuntu-20-04-installation/2/),
using the preinstalled Python 3.8.10. If the Pi seems to freeze, leave it alone for a while. Give it 15-20 minutes.
You can use `top` to monitor the memory usage. If the free Swap is 0 and the available memory close to 0, 
and it doesn't recover unplug it, (optionally enable the virtenv) and restart by using your last command.
Usually, the 'pip install'. Above all don't panic.

### 4.1) Preconditions
SD card of 16 MB or more

```console
    $ cat /etc/os-release | grep PRETTY_NAME
    PRETTY_NAME="Ubuntu 20.04.3 LTS"
```

```console
    $ cat /proc/cpuinfo | grep Model
    Model           : Raspberry Pi 400 Rev 1.0 
```

```console
    $ python3 --version
    Python 3.8.10
```

### 4.2) Install the dependencies
```console
    $ sudo apt-get install make gcc libgtk-3-dev libgstreamer-gl1.0-0 freeglut3 freeglut3-dev python3-gst-1.0 libglib2.0-dev ubuntu-restricted-extras libgstreamer-plugins-base1.0-dev
```

### 4.3) Get and install wxPython
```console
    $ python3 -m pip install wxPython
    $ python3
    import wx
    wx.__version__
    exit()
```


## 5) Choose your USB Sound Card

Execute first the command `alsamixer` to ensure that the sound card is recorgnized and in proper order of functioning.
Make sure that sound can be captured from it, and that the input volume is between 80 and 90.

Read the help of find_alsa_devices.py and follow it.
Then connetc line out of the sound card with line in of the same sound card.

```console
    $ cd ~/supersid/supersid
    $ python3 find_alsa_devices.py --help | less
    $ python3 -u find_alsa_devices.py 2>&1
```

The execution may take some minutes. Idealy a working configuration is found and the supersid.cfg settings are reported in the end.
If this fails, you may want to connect a frequency generator to the line in and set it to 10 kHz.

The frequency generator may by 

- a real frequency generator device
- a tablet or a smartphone running a frequency generator app
- the line out of a PC geneating the test frequency

It is possible to generate the test frequency with the *speaker-test* tool belonging to the *alsa-utils*.

Assuming you are using the `speaker-test` tool connect the line out with the line in and do the following.
You may have to adapt the device name to match your audio hardware. `aplay -L` will deliver a list of candidates.
Here the builtin ACL662 of the Lenovo PC is used.

In one console generate the test frequency.
```console
    $ speaker-test -Dplughw:CARD=Generic,DEV=0 -c 2 -t sine -f 10000 -X
```

In another console search for the suitable device. Replace 'CARD=Generic' with the device of interrest.
```console
    $ cd ~/supersid/supersid
    $ python3 -u find_alsa_devices.py -t=external -d="CARD=Generic" 2>&1 | grep OK
```

Lets assume, you got the output below (actually it is much longer, these are just two interresting snippets).
The first one shows an unstable configuration. In one second it works, in the next it fails.
You see the failure when the frequency is wrong (i.e. 0 Hz in this example).

Select a combination with properties in this order:

- it yields a duration of 1 s and the expected frequency in each regression
- the highest possible sampling rate 192000 is better than 96000, which is better than 48000
- a format using highest number of bits S32_LE is better than S24_3LE, which is better than S16_LE

```example
    192000, alsaaudio, default:CARD=Generic, S32_LE , 1024,  1, OK, 1.00 s, 0 Hz
    192000, alsaaudio, default:CARD=Generic, S32_LE , 1024,  2, OK, 1.00 s, 0 Hz
    192000, alsaaudio, default:CARD=Generic, S32_LE , 1024,  3, OK, 1.00 s, 9984 Hz
    192000, alsaaudio, default:CARD=Generic, S32_LE , 1024,  4, OK, 1.00 s, 9984 Hz
    192000, alsaaudio, default:CARD=Generic, S32_LE , 1024,  5, OK, 1.00 s, 9984 Hz
    192000, alsaaudio, default:CARD=Generic, S32_LE , 1024,  6, OK, 1.00 s, 9984 Hz
    192000, alsaaudio, default:CARD=Generic, S32_LE , 1024,  7, OK, 1.00 s, 0 Hz
    192000, alsaaudio, default:CARD=Generic, S32_LE , 1024,  8, OK, 1.00 s, 9984 Hz
    192000, alsaaudio, default:CARD=Generic, S32_LE , 1024,  9, OK, 1.00 s, 9984 Hz
    192000, alsaaudio, default:CARD=Generic, S32_LE , 1024, 10, OK, 1.00 s, 9984 Hz
    ...
    192000, alsaaudio, plughw:CARD=Generic,DEV=0, S32_LE , 1024,  1, OK, 1.01 s, 9984 Hz
    192000, alsaaudio, plughw:CARD=Generic,DEV=0, S32_LE , 1024,  2, OK, 1.01 s, 9984 Hz
    192000, alsaaudio, plughw:CARD=Generic,DEV=0, S32_LE , 1024,  3, OK, 1.01 s, 9984 Hz
    192000, alsaaudio, plughw:CARD=Generic,DEV=0, S32_LE , 1024,  4, OK, 1.01 s, 9984 Hz
    192000, alsaaudio, plughw:CARD=Generic,DEV=0, S32_LE , 1024,  5, OK, 1.01 s, 9984 Hz
    192000, alsaaudio, plughw:CARD=Generic,DEV=0, S32_LE , 1024,  6, OK, 1.01 s, 9984 Hz
    192000, alsaaudio, plughw:CARD=Generic,DEV=0, S32_LE , 1024,  7, OK, 1.01 s, 9984 Hz
    192000, alsaaudio, plughw:CARD=Generic,DEV=0, S32_LE , 1024,  8, OK, 1.01 s, 9984 Hz
    192000, alsaaudio, plughw:CARD=Generic,DEV=0, S32_LE , 1024,  9, OK, 1.01 s, 9984 Hz
    192000, alsaaudio, plughw:CARD=Generic,DEV=0, S32_LE , 1024, 10, OK, 1.01 s, 9984 Hz
```

Here 192000, alsaaudio, plughw:CARD=Generic,DEV=0, S32_LE, 1024 is a good choice,
while 192000, alsaaudio, default:CARD=Generic, S32_LE , 1024 is not working because the captured frequency is not consistently close to 10 kHz.
Cross-check with `sampler.py` the setting are working as epected.
The line with the duration and the peak frequency is the relevant one.

```console
   $ python3 -u sampler.py -s=192000 -m=alsaaudio -d="plughw:CARD=Generic,DEV=0" -f=S32_LE -p=1024 2>&1
```

This may be the output:
```example
    Accessing 'plughw:CARD=Generic,DEV=0' at 192000 Hz via alsaaudio format 'S32_LE', ...
    alsaaudio device 'plughw:CARD=Generic,DEV=0', sampling rate 192000, format S32_LE, periodsize 1024
    alsaaudio 'plughw:CARD=Generic,DEV=0' at 192000 Hz
    192000 <class 'numpy.int64'> read from alsaaudio 'plughw:CARD=Generic,DEV=0', shape (192000,), format S32_LE, duration 1.01 sec, peak freq 9984 Hz
    [ 1064932352  1074352000  -789722880 -1081461760 -1076092544 -1078001024
     -1071956096 -1069945216 -1077227008 -1067823744]
    Vector sum -32073466112
```

The corresponding lines of the configuration file 'supersid.cfg':
```example
    [PARAMETERS]
    audio_sampling_rate = 192000

    [Capture]
    Audio = alsaaudio
    Device = plughw:CARD=Generic,DEV=0
    Format = S32_LE
    PeriodSize = 1024
```


## 6) Troubleshooting issues with the sound card.
This section is not meant as exhaustive discussion how to detect and configure the sound card but
more as a list of tools which may help to do so. For further details you'll have to use search engines.

In the given example the following setup is present:

- A builtin *Realtek Audio Codec ALC662 rev3*.
- A *Creative Sound Blaster Play!* connected to USB

Install several utilities.
```console
    $ sudo apt-get install alsa-base alsa-utils pulseaudio-utils hwinfo
```

Add user to audio group. Lets assume your username is *klaus* and it is missing in the audio group.
```console
    $ grep audio /etc/group
    audio:x:29:pulse,asterisk
    $ sudo usermod -a -G audio klaus
    $ grep audio /etc/group
    audio:x:29:pulse,asterisk,klaus
```

Is the sound card listed as PCI or USB device?
In reality the putput is much longer. Here it is restricted to the relevant lines.
```console
    $ lspci | grep -i audio
    00:01.1 Audio device: Advanced Micro Devices, Inc. [AMD/ATI] Kabini HDMI/DP Audio
    00:09.0 Host bridge: Advanced Micro Devices, Inc. [AMD] Carrizo Audio Dummy Host Bridge
    00:09.2 Audio device: Advanced Micro Devices, Inc. [AMD] Family 15h (Models 60h-6fh) Audio Controller

    $ lsusb
    Bus 001 Device 016: ID 041e:30d3 Creative Technology, Ltd Sound Blaster Play!
```

Is the sound card listed as card in /proc/asound?
```console
    $ cat /proc/asound/cards
     0 [HDMI           ]: HDA-Intel - HDA ATI HDMI
                          HDA ATI HDMI at 0xfeb64000 irq 46
     1 [Generic        ]: HDA-Intel - HD-Audio Generic
                          HD-Audio Generic at 0xfeb60000 irq 47
     2 [U0x41e0x30d3   ]: USB-Audio - USB Device 0x41e:0x30d3
                          USB Device 0x41e:0x30d3 at usb-0000:00:10.0-2.2, full speed
```
0 [HDMI           ] is the audio output via HDMI.
1 [Generic        ] is the builtin ALC622.
2 [U0x41e0x30d3   ] is the Sound Blaster at the USB port.

Yet another view on the sound hardware. This generates a longer output which is not repeated here.
```console
    $ hwinfo --sound
```

Is the sound card listed by arecord?
```console
    $ arecord -l
    $ arecord -L
```

Is the voluem too low or the channel muted?
Set the volume to be between 80% and 90%, unmute the relevant channels.
```console
    $ alsamixer
```

Generate a test tome and connect line out to line in.
```console
    $ speaker-test -Dplughw:CARD=Generic,DEV=0 -c 2 -t sine -f 10000 -X
```


## 7) Adapt the your supersid\Config\supersid.cfg file

See [ConfigHelp.md](./ConfigHelp.md)


## 8) Start the SuperSID program

```console
    $ cd ~/supersid/supersid
    $ python3 supersid.py -c=../Config/supersid.cfg
```
