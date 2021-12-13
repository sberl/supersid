# SuperSID on Raspberry Pi 3 with Rapberry OS

## Preparation

[Set up your Raspberry Pi](https://www.raspberrypi.com/documentation/computers/getting-started.html#setting-up-your-raspberry-pi) with the image **Raspberry OS (32-bit)**. AT the date of the installation this corresponds to *buster*.
Boot on the new micro-SD card, follow normal process for any fresh system install. Connect to the internet.

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
    $ sudo apt-get install libasound2-dev
    $ sudo apt-get install libatlas-base-dev

    $ cd ~/supersid
    $ pip3 install -r requirements.txt
```

Optional and not required. Install when you want to test additonal audio libraries:

```console
    $ sudo apt install libportaudio2
    $ pip3 install sounddevice
    $ pip3 install PyAudio
```


## 4) Optional: Build and install wxPython

Build and install wxPython only if you really want to have wxPython, e.g. to test the scripts with 'viewer=wx' on the Pi.
The installation is time consuming.

This guide is an adapted short form of [Build WxPython On Raspberry Pi](https://wiki.wxpython.org/BuildWxPythonOnRaspberryPi),
using the preinstalled Python 3.7. If the Pi seems to freeze, leave it alone for a while. Give it 15-20 minutes.
You can use `top` to monitor the memory usage. If the free Swap is 0 and the available memory close to 0,
and it doesn't recover unplug it, (optionally enable the virtenv) and restart by using your last command.
Usually, the 'pip install'. Above all don't panic.

### 4.1) Preconditions
SD card of 16 MB or more

```console
    $ cat /etc/os-release | grep PRETTY_NAME
    PRETTY_NAME="Raspbian GNU/Linux 10 (buster)"
```

```console
    $ cat /proc/cpuinfo | grep Model
    Model           : Raspberry Pi 3 Model B Rev 1.2
```

```console
    $ python3 --version
    Python 3.7.3
```

### 4.2) Install the dependencies
```console
    $ sudo apt-get install dpkg-dev build-essential libjpeg-dev libtiff-dev libsdl1.2-dev libgstreamer-plugins-base0.10-dev libnotify-dev freeglut3 freeglut3-dev libwebkitgtk-dev libghc-gtk3-dev libwxgtk3.0-gtk3-dev python3.7-dev
```

### 4.3) Limit the number of parallel make jobs
```console
    $ sudo mv /usr/bin/make /usr/bin/make.org
    $ sudo nano /usr/bin/make
        make.org $* --jobs=2
        # save and exit with Ctrl+s, Ctrl+x
    $ sudo chmod a+x /usr/bin/make
```

### 4.4) Get and install wxPython
```console
    $ cd ~
    $ wget https://files.pythonhosted.org/packages/b9/8b/31267dd6d026a082faed35ec8d97522c0236f2e083bf15aff64d982215e1/wxPython-4.0.7.post2.tar.gz
    $ tar xf wxPython-4.0.7.post2.tar.gz
    $ cd wxPython-4.0.7.post2
    $ pip3 install Pygments==2.5.1
    $ pip3 install -r requirements.txt
    $ python3 build.py build bdist_wheel
    $ cd ~/wxPython-4.0.7.post2/dist
    $ pip3 install wxPython-4.0.7.post2-cp37-cp37m-linux_armv7l.whl
    $ cd ~/wxPython-4.0.7.post2/demo
    $ python3 demo.py
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
Here the builtin audio output of the RPi 3b is used.

In one console generate the test frequency.
```console
    $ speaker-test -Dplughw:CARD=Headphones,DEV=0 -c 2 -t sine -f 10000 -X
```

In another console search for the suitable device. Replace 'plughw:CARD=Dongle,DEV=0' with the device of interrest.
```console
    $ cd ~/supersid/supersid
    $ python3 -u find_alsa_devices.py -t=external -d="plughw:CARD=Dongle,DEV=0" 2>&1 | grep OK
```

Lets assume, you got the output below (actually it is much longer, this is just an interresting snippet).

Select a combination with properties in this order:

- it yields a duration of 1 s and the expected frequency in each regression
- the highest possible sampling rate 192000 is better than 96000, which is better than 48000
- a format using highest number of bits S32_LE is better than S24_3LE, which is better than S16_LE

```example
     96000, alsaaudio, plughw:CARD=Dongle,DEV=0, S24_3LE, 1024,  1, OK, 1.00 s, 9984 Hz
     96000, alsaaudio, plughw:CARD=Dongle,DEV=0, S24_3LE, 1024,  2, OK, 1.00 s, 9984 Hz
     96000, alsaaudio, plughw:CARD=Dongle,DEV=0, S24_3LE, 1024,  3, OK, 1.01 s, 9984 Hz
     96000, alsaaudio, plughw:CARD=Dongle,DEV=0, S24_3LE, 1024,  4, OK, 1.00 s, 9984 Hz
     96000, alsaaudio, plughw:CARD=Dongle,DEV=0, S24_3LE, 1024,  5, OK, 1.00 s, 9984 Hz
     96000, alsaaudio, plughw:CARD=Dongle,DEV=0, S24_3LE, 1024,  6, OK, 1.00 s, 9984 Hz
     96000, alsaaudio, plughw:CARD=Dongle,DEV=0, S24_3LE, 1024,  7, OK, 1.00 s, 9984 Hz
     96000, alsaaudio, plughw:CARD=Dongle,DEV=0, S24_3LE, 1024,  8, OK, 1.01 s, 9984 Hz
     96000, alsaaudio, plughw:CARD=Dongle,DEV=0, S24_3LE, 1024,  9, OK, 1.01 s, 9984 Hz
     96000, alsaaudio, plughw:CARD=Dongle,DEV=0, S24_3LE, 1024, 10, OK, 1.01 s, 9984 Hz
```

Here 96000, alsaaudio, plughw:CARD=Dongle,DEV=0, S24_3LE, 1024 is a good choice.
Cross-check with `sampler.py` the setting are working as epected.
The line with the duration and the peak frequency is the relevant one.

```console
   $ python3 -u sampler.py -s=96000 -m=alsaaudio -d="plughw:CARD=Dongle,DEV=0" -f=S24_3LE -p=1024 2>&1
```

This may be the output:
```example
    Accessing 'plughw:CARD=Dongle,DEV=0' at 96000 Hz via alsaaudio format 'S24_3LE', ...
    alsaaudio device 'plughw:CARD=Dongle,DEV=0', sampling rate 96000, format S24_3LE, periodsize 1024
    alsaaudio 'plughw:CARD=Dongle,DEV=0' at 96000 Hz
     96000 <class 'numpy.int32'> read from alsaaudio 'plughw:CARD=Dongle,DEV=0', shape (96000,), format S24_3LE, duration 1.02 sec, peak freq 9984 Hz
    [-4204419 -4227590 -4237790 -2773916  2728695  4167792  4192484  4179326
      1628634 -4107804]
    Vector sum 49601975
```

The corresponding lines of the configuration file 'supersid.cfg':
```example
    [PARAMETERS]
    audio_sampling_rate = 96000

    [Capture]
    Audio = alsaaudio
    Device = plughw:CARD=Dongle,DEV=0
    Format = S24_3LE
    PeriodSize = 1024
```


## 6) Troubleshooting issues with the sound card.
This section is not meant as exhaustive discussion how to detect and configure the sound card but
more as a list of tools which may help to do so. For further details you'll have to use search engines.

In the given example the following setup is present:

- A builtin *bcm2835 Headphones*.
- A *VIA USB Dongle* connected to USB

Install several utilities.
```console
    $ sudo apt-get install alsa-base alsa-utils pulseaudio-utils hwinfo
```

Add user to audio group. Lets assume your username is *pi* and it is missing in the audio group.
Most likely there is nothing to do as the user pi will be be part of the audio group.
```console
    $ grep audio /etc/group
    audio:x:29:pulse
    $ sudo usermod -a -G audio pi
    $ grep audio /etc/group
    audio:x:29:pulse,pi
```

Is the sound card listed as USB device?
In reality the putput is much longer. Here it is restricted to the relevant lines.
```console
    $ lsusb
    Bus 001 Device 008: ID 040d:3400 VIA Technologies, Inc.
```

Is the sound card listed as card in /proc/asound?
```console
    $ cat /proc/asound/cards
     0 [Headphones     ]: bcm2835_headpho - bcm2835 Headphones
                          bcm2835 Headphones
     1 [Dongle         ]: USB-Audio - VIA USB Dongle
                          VIA Technologies Inc. VIA USB Dongle at usb-3f980000.usb-1.4, full speed
```
0 [Headphones     ] is the builtin audio line out.
1 [Dongle         ] is the VIA USB Dongle at the USB port.

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
    $ speaker-test -Dplughw:CARD=Headphones,DEV=0 -c 2 -t sine -f 10000 -X
```


## 7) Adapt the your supersid\Config\supersid.cfg file

See [ConfigHelp.md](./ConfigHelp.md)


## 8) Start the SuperSID program

```console
    $ cd ~/supersid/supersid
    $ python3 supersid.py -c=../Config/supersid.cfg
```
