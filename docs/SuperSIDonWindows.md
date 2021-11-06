# SuperSID on Windows

## 1) Install Python 3.9.7 (64 bit)
Python 3.9 has been chosen because wxPython is available as wheel for Python 3.9 but not for Python 3.10.

- Download [Python 3.9.7 (64-bit)](https://www.python.org/ftp/python/3.9.7/python-3.9.7-amd64.exe)
- Install *python-3.9.7-amd64.exe*
    - Customize installation, keep all selected, Next
    - Additionally select [x] Install for all users
    - Double check the install location cahnged to *C:\\Program Files\\Python39*
    - Install
    - Close

## 2) Get the latest supersid software
- You can simply go to [SuperSID](https://github.com/sberl/supersid). Press the green 'Code' button and click 'Download ZIP', **or** download [supersid-master.zip](https://github.com/sberl/supersid/archive/refs/heads/master.zip) directly.
- Then extract the zip to the folder where you want to install SuperSID.

**or**

- You can first install [Git for Windows](https://gitforwindows.org/).
- Then open a GIT console in the folder you want to install SuperSID.

```console
    $ git clone https://github.com/sberl/supersid.git
```

To update (pull) to the latest version, do:
```console
    $ cd ~/supersid
    $ git pull
```


## 3) Installing SuperSID

Open a `CMD` window. Lets assume the SuperSID installation folder would be *C:\temp\supersid*.
```console
    > cd C:\temp\supersid
    > "C:\Program Files\Python39\python.exe" -m pip install --upgrade pip
    > "C:\Program Files\Python39\python.exe" -m pip install matplotlib numpy pyparsing python-dateutil six pyephem wxPython sounddevice pipwin
    > "C:\Program Files\Python39\python.exe" -m pipwin install PyAudio
```


## 4) Choose your Soundcard

Identify the available audio library / host API / audio card / sample rate combinations. If you have grep available, you can filter the results.

- use `sampler.py` in order to get a complete list including the errors
- use `sampler.py | grep "duration 1\.[01]"` in order to get a compact list of the acceptable candidates
- use `sampler.py | grep "duration 1\.[01]" -B2 -A2` in order to get a verbose list of the acceptable candidates

```console
    > cd C:\temp\supersid\supersid
    > "C:\Program Files\Python39\python.exe" sampler.py | grep "duration 1\.[01]" -B2 -A2
```

Find the right card line you want to use based on the card name and the frequency you want to sample.
Make sure that the time is approximately one second, not fractions of a second and not multiples of a second.

Not all combinations detected by `sampler.py` are actually working. Experience with a "Realtek High Definition Audio" card which is capable to sample at 192 kHz is that the following combinations work:

- sounddevice, MME, [48000, 96000, 192000] kHz
- sounddevice, Windows DirectSound, [48000, 96000, 192000] kHz
- pyaudio, MME, [48000, 96000, 192000] kHz

Caution, some combinations seem to work (there is no error message, no crash) but the captured data is garbage. e.g.:

- sounddevice, Windows WDM-KS, [48000, 96000, 192000] kHz
- pyaudio, Widnows WASAPI, [192000] kHz

Selected:
```example
    Accessing 'MME: Eingang (Realtek High Definitio' at 192000 Hz via sounddevice, ...
    sounddevice 'MME: Eingang (Realtek High Definitio' at 192000 Hz
    192000 <class 'numpy.int16'> read from sounddevice 'MME: Eingang (Realtek High Definitio', shape (192000,), duration 1.12
    [ 0  0 -1  0  0  0  0 -1  0  0]
    Vector sum -2810
```

The important parts are in this line<br/>
**192000** <class 'numpy.int16'> read from **sounddevice** '**MME: Eingang (Realtek High Definition Audio)**', shape (192000,), duration 1.12

The corresponding lines of the configuration file 'supersid.cfg':
```example
    [PARAMETERS]
    audio_sampling_rate = 192000

    [Capture]
    Audio = sounddevice
    Card = MME: Eingang (Realtek High Definition Audio)
```

## 5) Adapt the your supersid\Config\supersid.cfg file

See [ConfigHelp.md](./ConfigHelp.md)

## 6) Start the SuperSID program

```console
    > cd C:\temp\supersid\supersid
    > "C:\Program Files\Python39\python.exe" supersid.py -c=..\Config\supersid.cfg
```
