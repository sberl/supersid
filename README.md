SuperSID
========

Cross-platform Sudden Ionospheric Disturbances (SID) monitor

Objectives
----------
Monitoring the Sudden Ionospheric Disturbances (SID) is an easy yet exciting Home Based Radio Astronomy Project. This project is an implementation of [Stanford SOLAR Center’s SuperSID][Standford].

The default SuperSID project software runs on Windows OS to record the pre-amplified signal received by the antenna with a “SuperSID Monitor”. 

This *SuperSID* project is an Open Source implementation that runs on Linux and Windows. The scripts are executable by Python 3.

This *SuperSID* includes a text mode which allows to turn your Raspberry Pi into a SID monitor (tested on Raspbian Wheezy & Pidora distro). TkInter in the default GUI to ensure Python 3 compatibility.


|Original Project  |Open Source SuperSID Project
|------------------|--------------------------------------
|Desktop/Laptop PC |Desktop/Laptop PC/Raspberry Pi (512Mb)
|Windows OS        |Linux and Windows OS
|Python 2.7        |Python 3.3+
|Any Soundcard     |USB External Soundcard
|SuperSID Monitor pre-amp.  |Direct connection to External Soundcard

Other improvements
------------------

supersid.py:
 - More options in the [configuration file (.cfg)] (docs/ConfigHelp.md)
 - Continue recording after interruption
 - Auto adjustment of the interval period for better accuracy
 - New extended file format with time stamp to the 1.000th of second
 - *sidfile.py* can be used as a utility to manipulate SID files

![tkgui_screenshot01](https://cloud.githubusercontent.com/assets/5303792/9287125/7e65cb9c-4339-11e5-9f5b-4c740b8e8d21.png)

supersid_plot.py:
 - Accepts multiple files to display up to 10 days in continue (wildcards possible)
 - Can connect to NOAA to draw the day's events
 - Can send the graph as PDF by email

Example: `./supersid_plot.py -f ~/Data/DAISYSG_2015-07-03.csv --web`

![figure_20150703](https://cloud.githubusercontent.com/assets/5303792/9287076/5c4f3eb4-4337-11e5-9db7-00391b9fcf40.png)

[Standford]: http://solar-center.stanford.edu/SID/sidmonitor/

