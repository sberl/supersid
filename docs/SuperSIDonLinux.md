# SuperSID on Linux (Ubuntu Server 20.04.3 LTS)

This has been tested on

- Raspberry Pi 400 4GB
- Lenovo PC
- Debian GNU/Linux 10 (Buster) on a Dell Vostro desktop PC

## Preparation

[Set up your Raspberry Pi](https://www.raspberrypi.com/documentation/computers/getting-started.html#setting-up-your-raspberry-pi)
with the image **UBUNTU SERVER 20.04.3 LTS (RPI 3/4/400)** *64 bit server OS
with long-term support for arm64 architectures*.  Boot on the new micro-SD card,
follow normal process for any fresh system install.  Connect to the internet.

Install the x-server.
```console
    $ sudo apt install xinit
```
Reboot.  X will start.  Do the language setup and further required settings like
WiFi, language, keyboard layout, time zone, ...  Verify in the settings your
sound card is set as input and output device.

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

Now do the following:
```console
    $ cd ~/supersid
    $ mkdir Data
    $ mkdir outgoing
```
These directories will be used to store the data that will be sent via ftp to
Stanford.

To update (pull) to the latest version, do:
```console
    $ cd ~/supersid
    $ git pull
```


## 2) Extra software

Time synchro over the Internet:
It is important that your system time of day clock is closely synchronized with
the actual UTC time.  Then the data you collect can be compared to data from
other sources such as other SuperSID users, and Xray flux data collected by
satellites.
If your machine does not have ntp installed then you want to install it:
```console
    $ sudo apt-get install ntpdate ntp
```

Follow the tutorial [Raspberry Pi sync date and time](https://victorhurdugaci.com/raspberry-pi-sync-date-and-time)

Optional: Virtual environment management for Python:
If your machine is being used for other purposes as well as SuperSID, you may
want to install SuperSID in its own virtual python environment.  This way you
will not be plagued with version conflicts with the various python packages
installed for different uses.  There are several different ways to set up a
virtual environment.  This is one that has worked for me.


https://docs.python.org/3/tutorial/venv.html

Install the venv package.
```console
    $ sudo python3 -m pip install virtualenv
```

For Ubuntu use the following command (matching your Python 3.x version):
```console
    $ python3 --version
    Python 3.8.10
    $ sudo apt install python3.8-venv
```


## 3) Installing SuperSID

### 3.1) optional virtual environment

This step is optional.  Creating your own environment allows to install libraries
in all freedom, without `sudo` and ensure you have a coherent and working set of
libraries (sound card).  If your Raspi is dedicated to SuperSID then you can skip
this step and install all globally.

From /home/pi:
```console
    $ cd ~/supersid
    # Create your virtual environement
    $ python3 -m venv supersid-env
    # Activate the newly created virtual environment
    $ source supersid-env/bin/activate
    # Install latest versions of package tools
    $ python -m pip install -U pip wheel setuptools
```

Your prompt should now start with '(supersid-env)'
This ensures that we run in Python 3.x as per current configuration.
Once `source supersid-env/bin/activate` is executed, `python` and `python3`
can be used synonymously.

### 3.2) Global or local installation

If this Linux system is dedicated to SuperSid or you do not plan to mix various
libraries: install at system level all the libraries.

For an local installation inside the virtual environment, first execute 'source
supersid-env/bin/activate'.
```console
    $ cd ~/supersid
    $ source supersid-env/bin/activate
```

Now install the system level packages you will need
```console
    $ sudo apt-get install python3-matplotlib
    $ sudo apt-get install python3-pip
    $ sudo apt-get install libasound2-dev
    $ sudo apt-get install libatlas-base-dev
    $ sudo apt-get install python3-numpy
    $ sudo apt-get install python3-pandas
    $ cd ~/supersid
    $ pip3 install -r requirements.txt
```

Optional and not required.  Install when you want to test additonal audio
libraries:
```console
    $ sudo apt install libportaudio2
    $ pip3 install sounddevice
    $ sudo apt-get install python3-pyaudio
```


## 4) Choose your USB Sound Card

First execute the command `alsamixer` to ensure that the sound card is
recognized and functioning properly.  Use F6 to choose the sound card you
will be using.  Make sure that sound can be captured from it, and that the
input volume is between 80 and 90.

Read the help of find_alsa_devices.py and follow it.  Then connect line out of
the sound card with line in of the same sound card.

```console
    $ cd ~/supersid/supersid
    $ python3 find_alsa_devices.py --help
    $ python3 -u find_alsa_devices.py 2>&1
```

The execution may take some minutes.  Ideally a working configuration is found
and the supersid.cfg settings are at the end of the output.  Add these lines to
your configuration file and go on to step 7 of this document.

If this fails, you may want to connect a frequency generator to the line in and
set it to 10 kHz.

The frequency generator may be:

- a real frequency generator device
- a tablet or a smartphone running a frequency generator app
- the line out of a PC generating the test frequency

It is possible to generate the test frequency with the *speaker-test* tool
belonging to the *alsa-utils*.

Assuming you are using the `speaker-test` tool connect the line out with the
line in and do the following.  You may have to adapt the device name to match
your audio hardware.  `aplay -L` will deliver a list of candidates.  Here the
builtin ACL662 of the Lenovo PC is used.

In one console generate the test frequency.
```console
    $ speaker-test -Dplughw:CARD=Generic,DEV=0 -c 2 -t sine -f 10000 -X
```

In another console search for the suitable device.  Replace 'CARD=Generic' with
the device of interest.
```console
    $ cd ~/supersid/supersid
    $ python3 -u find_alsa_devices.py -t=external -d="CARD=Generic" 2>&1 | grep OK
```

Let us assume, you got the output below (actually it is much longer, these are
just two interesting snippets).  The first one shows an unstable configuration.
In one second it works, in the next it fails.  You see the failure when the
frequency is wrong (i.e. 0 Hz in this example).

Select a combination with properties in this order:

- Duration of 1 second and the expected frequency in each regression
- Highest possible sampling rate.  192000 is better than 96000, which is better
  than 48000
- Format using highest number of bits.  S32_LE is better than S24_3LE, which is
  better than S16_LE

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
while 192000, alsaaudio, default:CARD=Generic, S32_LE , 1024 is not working
because the captured frequency is not consistently close to 10 kHz.
Cross-check with `sampler.py` the settings are working as expected.
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


## 5) Troubleshooting issues with the sound card.
This section is not meant as an exhaustive discussion how to detect and
configure the sound card, but more as a list of tools which may help you to do
so.  For further details you'll have to use search engines.  If this fails, you
may want to connect a frequency generator to the line in and set it to 10 kHz.

In the given example the following setup is present:

- A builtin *Realtek Audio Codec ALC662 rev3*.
- A *Creative Sound Blaster Play!* connected to USB

Install several utilities.
```console
    $ sudo apt-get install alsa-base alsa-utils pulseaudio-utils hwinfo
```

Add user to audio group.  Lets assume your username is *klaus* and it is missing
in the audio group.
```console
    $ grep audio /etc/group
    audio:x:29:pulse,asterisk
    $ sudo usermod -a -G audio klaus
    $ grep audio /etc/group
    audio:x:29:pulse,asterisk,klaus
```

Is the sound card listed as PCI or USB device?

In reality the output is much longer.  Here it is restricted to the relevant
lines.
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
- 0 [HDMI           ] is the audio output via HDMI.
- 1 [Generic        ] is the builtin ALC622.
- 2 [U0x41e0x30d3   ] is the Sound Blaster at the USB port.

Yet another view on the sound hardware.  This generates a longer output which is
not repeated here.
```console
    $ hwinfo --sound
```

Is the sound card listed by arecord?
```console
    $ arecord -l
    $ arecord -L
```

Is the volume too low or the channel muted?

Set the volume to be between 80% and 90%, unmute the relevant channels.
```console
    $ alsamixer
```

Generate a test tome and connect line out to line in.
```console
    $ speaker-test -Dplughw:CARD=Generic,DEV=0 -c 2 -t sine -f 10000 -X
```


## 6) Edit your supersid\Config\supersid.cfg file

See [ConfigHelp.md](./ConfigHelp.md)

Using the File Manager, navigate to ~/supersid/Config and open supersid.cfg
with a text editor.

Edit the file to add the information for your station.

Viewer can be either text or tk.
The text viewer is a basic text display.
The tk viewer will display the spectrograph which is useful in positioning the
antenna for the strongest signals.

Once you are confident that you are reliably collecting good data (with a
recognizable sunrise signature) you can begin to FTP data to Stanford.  In the
[FTP] section of supersid.cfg, set 'automatic_upload' to yes and add the
stations that you wish to send under 'call_signs'.  Separate the stations with
commas without spaces.  The file to be sent must be in 'supersid_format' or
'supersid_extended' format - one file for all stations.  Setting 'log_format'
to one of 'supersid_format', 'supersid_extended', 'both', 'both_extended' in
the supersid.cfg file will create the necessary file.

'supersid_extended' is a good option as it combines the most accuarte timestamp
with a compact format.

Using `log_format = both_extended` in the supersid.cfg file will create the
necessary file in 'supersid_extended' format and also a file for each station
in 'sid_extended' format.  The 'sid_extended' format files can be useful if a
plot file of an individual station is desired.

Sending the ftp is accomplished by the program 'ftp_to_stanford.py' which is
called by 'supersid.py' at midnight (UTC).  'ftp_to_stanford.py' reads the
supersid file from `~/supersid/Data/` directory and converts them to filtered
files for each station.  These are stored in `~/supersid/outgoing` and sent via
ftp.


## 7) Start the SuperSID program

```console
    $ cd ~/supersid/supersid
    $ ./supersid.py
```


## 8) Plot commands

In a terminal window, navigate to /home/pi/supersid/supersid

Replace filename.csv with the name of the file you want to plot

For a standard plot:
```console
    $ ./supersid_plot.py -f ../Data/filename.csv
```

To create a plot and save it without viewing:
```console
    $ ./supersid_plot.py -f ../Data/filename.csv -n -p ../Data/filename.pdf
```

For a plot containing NOAA flare data:
```console
    $ ./supersid_plot.py -w -f ../Data/filename.csv
```

For an interactive plot that enables you to turn stations off/on:
```console
    $ ./supersid_plot_gui.py ../Data/filename.csv
```

For the above, use the file in supersid_format that contains all of the stations
as listed in your supersid.cfg.

For a plot that will be sent via email:
```console
    $ ./supersid_plot.py -n -f ../Data/filename.csv -e xxxx@gmail.com
```

The supersid.cfg file must include the [Email] section containing the appropriate
information.

supersid_plot arguments:

- -h help
- -f location and name of csv file
- -c location and name of config file
- -n create plot without showing on the screen
- -p create PDF or image file;
     examples: -p myplot.pdf, -p myplot.jpg, -p myplot.png, -p myplot.tiff
- -e destination email address
- -w retrieve NOAA flare information
