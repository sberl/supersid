# SuperSID on Raspberry Pi with Rapberry OS

This has been tested on

Raspberry Pi Zero W
Raspberry Pi Zero 2 W
Raspberry Pi 3 Model B
Raspberry Pi 3 Model B+
Raspberry Pi 4 Model B

## Preparation

[Set up your Raspberry Pi](https://www.raspberrypi.com/documentation/computers/getting-started.html#setting-up-your-raspberry-pi)
with the image **Raspberry OS (32-bit)**.  Current version as of 2022-01-03 is
*bullseye*. Boot on the new micro-SD card, follow normal process for any
fresh system install.  Connect to the internet.

Execute the classic:
```console
    $ sudo apt-get update
    $ sudo apt-get upgrade
```

If you intend to access your system remotely you must enable SSH and VNC.
To do this, click on the Raspberry icon in the upper left of the screen.
From the drop down, choose Preferences > Raspberry Pi Configuration.  Under the
Interface tab, Enable SSH & VNC.  Move your cursor to the upper right of the
window and hover over the icon that will show the wlan0 (WiFi) address that
your router has assigned to the RPi.  You will need to record this address
(192.168.1.xxx) in order to access via SSH or VNC.  When complete, open a
terminal window type fbset to find the current screen resolution and record
it.  In the event that VNC gives you the error 'currently cannot show desktop'
you will have to lower the screen resolution.


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

If you installed *Raspbian bullseye*, ntp is already installed and configured.
```console
    $ timedatectl status
```
You should read in one of the lines 'NTP service: active'.

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
    $ python3 -m pip install -U pip wheel setuptools
```

Your prompt should now start with '(supersid-env)'
This ensures that we run in Python 3.x as per current configuration.

### 3.2) Global or local installation

If this Raspberry Pi is dedicated to SuperSid or you do not plan to mix various
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
    $ sudo apt-get install libasound2-dev
    $ sudo apt-get install libatlas-base-dev
    $ cd ~/supersid
    $ pip3 install -r requirements.txt
```

Optional and not required.  Install when you want to test additonal audio
libraries:
```console
    $ sudo apt install libportaudio2
    $ pip3 install sounddevice
    $ pip3 install PyAudio
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
    $ python3 find_alsa_devices.py --help | less
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
built-in audio output of the RPi 3b is used.

In one console generate the test frequency.
```console
    $ speaker-test -Dplughw:CARD=Headphones,DEV=0 -c 2 -t sine -f 10000 -X
```

In another console search for the suitable device.  Replace
'plughw:CARD=Dongle,DEV=0' with the device of interest.
```console
    $ cd ~/supersid/supersid
    $ python3 -u find_alsa_devices.py -t=external -d="plughw:CARD=Dongle,DEV=0" 2>&1 | grep OK
```

Let us assume, you got the output below (actually it is much longer, this is
just an interesting snippet).

Select a combination with properties in this order:

- Duration of 1 second and the expected frequency in each regression
- Highest possible sampling rate.  192000 is better than 96000, which is better
  than 48000
- Format using highest number of bits.  S32_LE is better than S24_3LE, which is
  better than S16_LE

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
Cross-check with `sampler.py` the settings are working as expected.
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


## 5) Troubleshooting issues with the sound card.
This section is not meant as an exhaustive discussion how to detect and
configure the sound card, but more as a list of tools which may help you to do
so.  For further details you'll have to use search engines.  If this fails, you
may want to connect a frequency generator to the line in and set it to 10 kHz.

In the given example the following setup is present:

- A built-in *bcm2835 Headphones*.
- A *VIA USB Dongle* connected to USB

Install several utilities.
```console
    $ sudo apt-get install alsa-base alsa-utils pulseaudio-utils hwinfo
```

Add user to audio group.  Lets assume your username is *pi* and it is missing
in the audio group.
Most likely there is nothing to do as the user pi will be be part of the audio group.
```console
    $ grep audio /etc/group
    audio:x:29:pulse
    $ sudo usermod -a -G audio pi
    $ grep audio /etc/group
    audio:x:29:pulse,pi
```

Is the sound card listed as USB device?

In reality the output is much longer.  Here it is restricted to the relevant
lines.
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
- 0 [Headphones     ] is the built-in audio line out.
- 1 [Dongle         ] is the VIA USB Dongle at the USB port.

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
    $ speaker-test -Dplughw:CARD=Headphones,DEV=0 -c 2 -t sine -f 10000 -X
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
There are three arguments that can be used with supersid.py  
Using -r will allow supersid.py to read an existing csv file and add new data to it.  This can be useful in the event of a power interruption.  
Using -c will allow you to specify a cfg file  
Using -v will allow you to specify a different viewer than that which is listed in your cfg file.  Options are either text or tk  


## 8) SD Card Backup

It is advisable to make a copy of your SD card once you determine that
everything is set up and working.  Under Accessories there is a utility called
SD Card Copier that can be used along with a USB SD card reader to clone your
card.


## 9) Automatic Restart After Power Outage

If you would like this option, do the following:

```console
    $ sudo nano /etc/xdg/lxsession/LXDE-pi/autostart
```

add the following to the bottom of the file:

```
    @lxterminal --command “/home/pi/runSID.sh”
```

Save and Exit


In the /home/pi directory, create a file called runSID.sh

```console
    $ nano runSID.sh
```
add the following to the file:

```
    #!/bin/sh
    sleep 30
    cd /home/pi/supersid/supersid
    ./supersid.py
```

Save and Exit

Make it executable by doing:

```console
    $ sudo chmod +x runSID.sh
```


## 10) Plot commands

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
