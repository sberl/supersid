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
    $ sudo apt-get install libasound2-dev
    $ pip3 install -r requirements.txt
```

Optional and not required. Install when you want to test additonal audio libraries:

```console
    sudo apt install libportaudio2
    pip3 install sounddevice
    pip3 install PyAudio
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


## 5) Choose your USB Soundcard

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
