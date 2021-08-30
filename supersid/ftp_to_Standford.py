#!/usr/bin/python3

"""
Send SID data files to Standford FTP server.

Name:        ftp_to_Standford.py
Author:      Eric Gibert

Created:     10-08-2012 as send_to_standford.py
Updated:     31-07-2015
Copyright:   (c) eric 2012
Licence:     <your licence>

Script's Arguments:
-c|--config supersid.cfg : the configuration file for its [FTP]
   and [PARAMETERS] sections
-y|--yesterday : to send yesterday's superSID file
    [data_path/<monitor_id>_YYYY_MM_DD.csv]
[filename1 filename2 ...]: optional list of files to send

New section in the configuration file:
[FTP]
automatic_upload = yes
ftp_server = sid-ftp.stanford.edu
ftp_directory = /incoming/SuperSID/NEW/
local_tmp = /home/eric/supersid/Private/tmp
call_signs = NWC:10000,JJI:100000

"""
from __future__ import print_function   # use the new Python 3 'print' function
import argparse
from os import path
import sys
import ftplib
from socket import gaierror
from datetime import datetime, timedelta
from sidfile import SidFile
from config import Config, FILTERED, RAW


def exist_file(x):
    """Check that file exists but does not open it."""
    if not path.isfile(x):
        raise argparse.ArgumentError("{0} does not exist".format(x))
    return x


def convert_supersid_to_sid(sid, stations):
    """Convert a supersid format data file to one or more sid format files.

    returns a list of sid format files to send
    """
    generated_files = []
    for station in stations:
        print("Sending data from: ", station)
        # if necessary, apply a multiplicator factor to the signal
        # of one station [NWC:100000]
        if ':' in station:
            station_name, factor = station.split(':')
            factor = int(factor)
        else:
            station_name, factor = station, 1

        if station_name not in sid.stations:
            # strange: the desired station in not found in the file
            print("Warning:", station_name,
                  "is not in the data file", input_file)
            continue

        if factor > 1:
            station_index = sid.get_station_index(station_name)
            sid.data[station_index] *= factor

        # generate the SID file of that station
        # UTC_StartTime = 2014-05-31 00:00:00
        file_startdate = sid.sid_params['utc_starttime']
        file_name = "{}{}{}_{}_{}.csv".format(cfg['local_tmp']
                                              or cfg["data_path"],
                                              path.sep,
                                              cfg['site_name'],
                                              station_name,
                                              file_startdate[:10])
        # if the original file is filtered then we can save it
        # "as is" else we need to apply_bema i.e. filter it
        sid.write_data_sid(station_name, file_name, FILTERED,
                           extended=False,
                           apply_bema=sid.sid_params['logtype'] == RAW)
        generated_files.append(file_name)
    return generated_files


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", dest="cfg_filename",
                        required=True, type=exist_file,
                        help="Supersid configuration file")
    parser.add_argument("-y", "--yesterday", action="store_true",
                        dest="askYesterday", default=False,
                        help="Yesterday's date is used for the file name.")
    args, file_list = parser.parse_known_args()
    # read the configuration file
    cfg = Config(args.cfg_filename)
    # what stations are to be selected from the input file(s) ?
    stations = (cfg['call_signs'].split(",")
                if cfg['call_signs'] else
                [s['call_sign'] for s in cfg.stations])  # else all stations

    # file list
    if args.askYesterday:
        yesterday = datetime.utcnow() - timedelta(days=1)
        # We need to figure out the names of yesterdays files
        if cfg['log_format'] == 'sid_format':
            print("log_format is sid_format")
            for station_call in stations:
                station_call = station_call.strip()
                file_list.append("{}{}{}_{}_{}-{:02d}-{:02d}.csv"
                                 .format(cfg['data_path'],
                                         path.sep, cfg['site_name'],
                                         station_call,
                                         yesterday.year,
                                         yesterday.month,
                                         yesterday.day))
            print(file_list)

        elif cfg['log_format'] == 'supersid_format':
            print("log_format is supersid_format")
            file_list.append("{}{}{}_{}-{:02d}-{:02d}.csv"
                             .format(cfg['data_path'],
                                     path.sep, cfg['site_name'],
                                     yesterday.year,
                                     yesterday.month,
                                     yesterday.day))
        else:
            print("unsupported log format")
    # generate all the SID files ready to send in the local_tmp file
    files_to_send = []
    for input_file in file_list:
        if path.isfile(input_file):
            sid = SidFile(input_file, force_read_timestamp=True)
            if sid.sid_params['contact'] == "" and cfg['contact'] != "":
                sid.sid_params['contact'] = cfg['contact']

            print(sid.sid_params)

            if sid.isSuperSID:
                # SuperSID format files need to be converted to a set of
                # one or more SID format files before they can be uploaded
                # to the Stanford FTP server
                # Pull all this out into a seperate function
                # convert_supersid_to_sid(sid, stations)
                # returns a list of files to send
                if sid.sid_params['contact'] == "" and cfg['contact'] != "":
                    sid.sid_params['contact'] = cfg['contact']
                files_to_send = convert_supersid_to_sid(sid, stations)
            else:
                files_to_send.append(input_file)
    print("Main files_to_send: ", files_to_send)
    # now sending the files by FTP
    if files_to_send and cfg['automatic_upload'] == 'YES':
        print("Opening FTP session with", cfg['ftp_server'])
        data = []

        try:
            ftp = ftplib.FTP(cfg['ftp_server'])
        except gaierror as e:
            print(e)
            print("Check ftp_server in .cfg file")
            sys.exit(1)

        ftp.login("anonymous", cfg['contact'])
        ftp.cwd(cfg['ftp_directory'])
        print("putting files to ", cfg['ftp_directory'])
        # ftp.dir(data.append)
        for f in files_to_send:
            print("Sending", f)
            try:
                ftp.storlines("STOR " + path.basename(f), open(f, "rb"))
            except ftplib.error_perm as err:
                print("Error sending", path.basename(f), ":", err)
        ftp.quit()
        print("FTP session closed.")

        for line in data:
            print("-", line)
