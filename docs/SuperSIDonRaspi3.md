# SuperSID on Raspberry Pi with Rapberry OS

## Preparation

[Set up your Raspberry Pi](https://www.raspberrypi.com/documentation/computers/getting-started.html#setting-up-your-raspberry-pi) with the image **Raspberry OS (32-bit)**. At the date of the installation this corresponds to *buster*.
Boot on the new micro-SD card, follow normal process for any fresh system install. Connect to the internet.

Execute the classic:
```console
    $ sudo apt-get update
    $ sudo apt-get upgrade
```

If you intend to access your system remotely you must enable SSH and VNC.
To do this, click on the Raspberry icon in the upper left of the screen.
From the drop down, choose Preferences > Raspberry Pi Configuration. Under the Interface tab, Enable SSH & VNC.
Move your cursor to the upper right of the window and hover over the icon that will show the wlan0 (WiFi) address that your router has assigned to the RPi. You will need to record this address (192.168.1.xxx) in order to access via SSH or VNC.
When complete, open a terminal window type fbset to find the current screen resolution and record it.


## 1) Get the latest supersid software

Get the source from GitHub.com

```console
    $ cd ~
    $ git clone https://github.com/sberl/supersid.git
```

Now do the following:
```console
    ~/supersid $ mkdir Data
    ~/supersid $ mkdir outgoing
```
These directories will be used to store the data that will be sent via ftp to Stanford.

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


## 4) Choose your USB Sound Card

Execute first the command `alsamixer` to ensure that the sound card is recognized and in proper order of functioning.
Use F6 to choose the sound card you will be using.
Make sure that sound can be captured from it, and that the input volume is between 80 and 90.

Read the help in find_alsa_devices.py and follow it.
Then connect line out of the sound card with line in of the same sound card.

```console
    $ cd ~/supersid/supersid
    $ python3 find_alsa_devices.py --help | less
    $ python3 -u find_alsa_devices.py 2>&1
```

The execution may take some minutes. Idealy a working configuration is found and the supersid.cfg settings are reported in the end.
If this fails, you may want to connect a frequency generator to the line in and set it to 10 kHz.

The frequency generator may be

- a real frequency generator device
- a tablet or a smartphone running a frequency generator app
- the line out of a PC generating the test frequency

It is possible to generate the test frequency with the *speaker-test* tool belonging to the *alsa-utils*.

Assuming you are using the `speaker-test` tool connect the line out with the line in and do the following.
You may have to adapt the device name to match your audio hardware. `aplay -L` will deliver a list of candidates.
Here the built-in audio output of the RPi 3b is used.

In one console generate the test frequency.
```console
    $ speaker-test -Dplughw:CARD=Headphones,DEV=0 -c 2 -t sine -f 10000 -X
```

In another console search for the suitable device. Replace 'plughw:CARD=Dongle,DEV=0' with the device of interest.
```console
    $ cd ~/supersid/supersid
    $ python3 -u find_alsa_devices.py -t=external -d="plughw:CARD=Dongle,DEV=0" 2>&1 | grep OK
```

Let us assume, you got the output below (actually it is much longer, this is just an interesting snippet).

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
This section is not meant as an exhaustive discussion how to detect and configure the sound card but
more as a list of tools which may help to do so. For further details you'll have to use search engines.

In the given example the following setup is present:

- A built-in *bcm2835 Headphones*.
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
0 [Headphones     ] is the built-in audio line out.
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


## 6) Edit your supersid\Config\supersid.cfg file

See [ConfigHelp.md](./ConfigHelp.md)

Using the File Manager, navigate to ~/supersid/Config and open supersid.cfg with a text editor.

Edit the file to add the information for your station.

Viewer can be either text or tk.
The text viewer is a basic text display.
The tk viewer will display the spectrograph which is useful in positioning the antenna for the strongest signals.

Once you are confident that you are reliably collecting good data (with a recognizable sunrise signature) you can begin to FTP data to Stanford.
In the [FTP] section of supersid.cfg, set 'automatic_upload' to yes and add the stations that you wish to send under 'call_signs'.
Separate the stations with commas without spaces.  The file to be sent must be in 'supersid_format' or 'supersid_extended' format - one file for all stations.
Setting 'log_format' to one of 'supersid_format', 'supersid_extended', 'both', 'both_extended' in the supersid.cfg file will create the necessary file.
'supersid_format' is a good option as it combines the most accuarte timestamp with a compact format.

Sending the ftp is accomplished by the program ftp_to_stanford.py which is called by supersid.py at midnight (UTC).
ftp_to_stanford.py uses the '~/supersid/outgoing' directory to store the files to be sent via ftp.


## 7) Start the SuperSID program

```console
    $ cd ~/supersid/supersid
    $ ./supersid.py
```


## 8) SD Card Backup

It is advisable to make a copy of your SD card once you determine that everything is set up and working.  Under Accessories there is a utility called SD Card Copier that can be used along with a USB SD card reader to clone your card.


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

For the above, use the file in supersid_format that contains all of the stations as listed in your supersid.cfg.

For a plot that will be sent via email:   
```console
    $ ./supersid_plot.py -n -f ../Data/filename.csv -e xxxx@gmail.com
```

The supersid.cfg file must include the [Email] section containing the appropriate information.

supersid_plot arguments:

-f        location and name of csv file

-c        location and name of config file

-n        create plot without showing on the screen

-p        create PDF or image file - ex: -p myplot.pdf, -p myplot.jpg, -p myplot.png, -p myplot.tiff

-e        destination email address

-w        retrieve NOAA flare information

