# SuperSID on Linux (Ubuntu Server 20.04.3 LTS)

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
without `sudo` and ensure you have a coherent and working set of libraries (soundcard).
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
    $ pip3 install -r requirements.txt
```

Optional and not required. Install when you want to test additonal audio libraries:

```console
    sudo apt install libportaudio2
    pip3 install sounddevice
    $ sudo apt-get install python3-pyaudio
```


## 4) Choose your USB Soundcard

Execute first the command `alsamixer` to ensure that the card is recorgnized and in proper order of functioning.
Make sure that sound can be captured from it, and that the input volume is between 80 and 90.

Do the following:

```console
    $ cd ~/supersid/supersid
    $ python3 sampler.py
```

Find the right card line you want to use based on the card name and the frequency you want to sample.
Make sure that the time is approximately one second, not fractions of a second and not multiples of a second.

```example
    alsaaudio sound card capture on sysdefault:CARD=External at 48000 Hz
    48000 bytes read from alsaaudio sound card capture on sysdefault:CARD=External (48000,)
```

The corresponding lines of the configuration file 'supersid.cfg':
```example
    [PARAMETERS]
    audio_sampling_rate = 48000

    [Capture]
    Audio = alsaaudio
    Card = External
    PeriodSize = 128
```

## 6) Adapt the your supersid\Config\supersid.cfg file

See [ConfigHelp.md](./ConfigHelp.md)

## 7) Start the SuperSID program

```console
    $ cd ~/supersid/supersid
    $ python3 supersid.py -c=../Config/supersid.cfg
```
