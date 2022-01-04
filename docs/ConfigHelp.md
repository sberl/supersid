# File Naming Convention and Location

SuperSID uses the parameters set in the provided configuration file passed as an argument on the command line. By convention, the file name is "supersid.cfg".
It is possible to have more than one configuration file to launch the SuperSID application with different parameters. For example to specify different list of Stations to monitor or to choose between graphic or text mode interface.

The file can be located in any accessible directory provided that the fully qualified path is given. In case no path is provided, the default path '../Config/supersid.cfg' will be used.
 
# File Organization

The configuration file is a simple text file formatted as a classic '.ini' structure i.e. sections with squared brackets and a list of pairs 'key=value"
 
The supported sections are:

  * [PARAMETERS](#id-section1)
  * [STATION_x](#id-section2) where x is a number in [1..n]
  * [Capture](#id-section3)
  * [Email](#id-section4)
  * [FTP](#id-section5)
  
<div id='id-section1'/>

## [PARAMETERS]

This section groups most of the parameters identifying your SuperSID monitor. Some optional parameters offer the possibility to change some default values used by the program.

### Monitor Identification

  * contact: email or phone number of the SuperSID owner. *Mandatory*
  * site_name: unique identification of the SuperSID monitor. *Mandatory*
  * monitor_id: unique id to distinguish the monitors running on one site
  * longitude: in decimal form
  * latitude: in decimal form
  * utc_offset:
  * time_zone:
  
### Log Parameters

  * audio_sampling_rate: **48000**, **96000** or **192000** (you can experiment with other values as long as your device supports them)
  * log_interval: number of seconds between two readings. Default is '**5**' seconds. Reading/sound capture lasts one second.
  * log_type: **filtered** or **raw**. When **filtered** is indicated, *bema_wing* function is called to smoothen the raw data before writting the file else in **raw** mode, captured data are written 'as is'. Note that *sidfile.py* can be used as an utility to apply 'bema_wing' function to an existing file (raw or not) to smoothen its data.
  * data_path: fully qualified path where files will be written. If not mentioned then '../Data/' is used. If the path is relative, then it is relative to the script folder.
  * log_format:
    - **sid_format**:<br />
      One file per station.<br />
      First data column as timestamp with *log_interval* increment, starting at at 00:00:00 UTC.<br />
      Second data column as captured value of the station.
    - **sid_extended**:<br />
      One file per station.<br />
      First data column is extended timestamp HH:MM:SS.mmmmmm,<br />
      Second data column as captured value of the station.
    - **supersid_format**:<br />
      All stations combined in one file.<br />
      No timestamp but one data column per station. Each line is *log_interval* seconds after the previous, first line at 00:00:00 UTC.<br />
      One data column per station with the captured values.<br />
      This configuration is suitable for [FTP] automatic_upload = yes.
    - **supersid_extended** (default):<br />
      All stations combined in one file.<br />
      First data column is extended timestamp HH:MM:SS.mmmmmm,<br />
      followed by one data column per station with the captured values.<br />
      This configuration is suitable for [FTP] automatic_upload = yes.
    - **both**:<br />
      The combination of **sid_format** and **supersid_format**.<br />
      This configuration is suitable for [FTP] automatic_upload = yes.
    - **both_extended**:<br />
      The combination of **sid_extended** and **supersid_extended**.<br />
      This configuration is suitable for [FTP] automatic_upload = yes.
  * hourly_save: **yes** / **no** (default). If **yes** then a raw file is written every hour to limit data loss.
  
### FTP to Standford server

Version 1.4: FTP information is no longer part of the [PARAMETERS] section. Refer to the [FTP] section below.
  
### Extra

  * scaling_factor: float, set it to **1.0**. The data captured from the sound card is multiplied with this value.
  * mode: [ignored] **Server**, **Client**, **Standalone** (default) . Reserved for future client/server dev.
  * viewer: **text** for text mode light interface or **tk** for TkInter GUI (default).
  * psd_min: float, min value for the y axis of the psd graph, **NaN** (default) means automatic scaling
  * psd_max: float, max value for the y axis of the psd graph, **NaN** (default) means automatic scaling
  * psd_ticks: int, number of ticks for the y axis of the psd graph, **0** (default) means automatic ticks.
    Fixed number of 'psd_ticks' works only in conjunction with 'psd_min' and 'psd_max'.
  * bema_wing: beta_wing parameter for sidfile.filter_buffer() calculation. Default is '**6**'.
  * paper_size: one of **A3**, **A4**, **A5**, **Legal**, **Letter**
  * number_of_stations: specify the number of stations to monitor. Each station is described within its own section.

<div id='id-section2'/>

## [STATION_x]

Each station to monitor is enumerated from 1 till n=*number_of_stations*. For each station, one must provide:

  * call_sign: Station ID (various VLF station lists exist like [AAVSO's] (http://www.aavso.org/vlf-station-list) and [Wikipedia's] (http://en.wikipedia.org/wiki/Very_low_frequency#List_of_VLF_transmissions))
  * frequency: emission frequency in Hz
  * color: [**r**, **g**, **b**, **c**, **m**, **k**] or [List of named colors](https://matplotlib.org/stable/gallery/color/named_colors.html) or [xkcd colors](https://matplotlib.org/stable/tutorials/colors/colors.html#xkcd-colors) to draw multiple graph together in *SuperSID_plot.py*.
  * channel: Default is **0**. Can optionally be set to **1** if [Capture] Channels = **2**. Channels (0, 1) correspond to the (left, right) channel of a stereo audio input.
  
<div id='id-section3'/>

## [Capture]

This section can be omitted if you plan to use the 'pyaudio' library. If you want to use the "alsaaudio" library then you can declare:

  * Audio: python library to use **alsaaudio** (default for Linux), **sounddevice** (default for Windows) or **pyaudio**
  * Card: [for alsaaudio only] card name for capture. The card name is incomplete, thus alsaaudio is guessing the device name. This is deprecated, use Device instead.
  * Device: device name for capture. **plughw:CARD=Generic,DEV=0** (default for Linux), **MME: Microsoft Sound Mapper - Input** (default for Windows).
  * Format: **S16_LE** (default), **S24_3LE**, **S32_LE**
  * PeriodSize: [for alsaaudio only] period size for capture. Default is '1024'.
  * Channels: [for alsaaudio only] number of channels tp be captured. Default is **1**, can be set to **2**.
  
<div id='id-section4'/>

## [Email]

The 'supersid_plot.py' program can send you an email with the attached plot as a PDF file. In order to use this feature, you must provide the information necessary to contact your email server as well as which email to use.

  * from_mail: sender's email
  * email_server: email server to use (SMPT)
  * email_port: email server's port (SMPT)
  * email_tls: email server requires TLS **yes** / **no** (default)
  * email_login: [optional] if your server requires a login for identification
  * email_password: [optional] if your server requires a password for identification
  
<div id='id-section5'/>

## [FTP]

Group all parameters to send data to an FTP server i.e. Standford data repository.

  * automatic_upload: [yes/no] if set to 'yes' then trigger the FTP data upload. Please refer to 'log_format' above for further details.
  * ftp_server: URL of the server (sid-ftp.stanford.edu)
  * ftp_directory: target folder on the FTP server where files should be written (on Standford's server: /incoming/SuperSID/NEW/)
  * local_tmp: local temporary directory used to write the files before their upload. If not mentioned then '../outgoing/' is used. If the path is relative, then it is relative to the script folder.
  * call_signs: list of recorded stations to upload. Not all recorded stations might be of interrest: list only the most relevant one(s).

## Comments

Comments are marked with a hash or a semicolon as the first character of the line.
```
   # This is a comment with a hash.
   ; This is another comment with a semicolon.
```
