#!/usr/bin/env python3
"""
Retrieve data from NOAA regarding X-ray solar flares (GOES).

Input Parameter is date of solar observation
    Date can be specified as either a datetime object, a date object,
    or a string of the form YYYYMMDD

Output:
    - datetime of start, high, end
    - classification (A, B, C, M, X...)

    This data can be used by the supersid_plot script to enrich the graph
    with the X-ray flares

    If the date is in the current year then FTP for the day's file is done,
    else the complete past year file is downloaded (and kept) then data is read

ftp://ftp.swpc.noaa.gov/pub/indices/events/20150629events.txt
https://www.ngdc.noaa.gov/stp/space-weather/solar-data/solar-features/solar-flares/x-rays/goes/xrs/goes-xrs-report_2014.txt
"""

import urllib.request
import urllib.error
import os
import sys
from os import path
from datetime import datetime, date, timezone
from supersid_common import script_relative_to_cwd_relative

NOAA_CACHE_FOLDER = path.join("..", "Private")

class NOAA_flares:
    """This object carries a list of all events of a given day."""

    ngdc_url = ("https://www.ngdc.noaa.gov/stp/space-weather/"
                "solar-data/solar-features/solar-flares/x-rays/goes/xrs/")

    def __init__(self, day):
        if isinstance(day, str):
            print("NOAA_flares: Initialize from string:", day)
            self.day = day[:8]  # limit to YYYYMMDD
        elif isinstance(day, (datetime, date)):
            print(f"NOAA_flares: Initialize from {type(day)} [{day}]")
            self.day = day.strftime('%Y%m%d')
        else:
            raise TypeError(
                "Unknown date format - expecting str 'YYYYMMDD' or "
                "datetime/date")

        # Code beyond this point assumes self.day is a string in 'YYYYMMDD' format
        if len(self.day) != 8 or not self.day.isdigit():
            raise ValueError("day must be a string in 'YYYYMMDD' format")

        print("NOAA_flares: day =", self.day)

        self.XRAlist = []

        # Starting in year 2017, NOAA makes the data available via FTP.
        # Earlier year data is available via HTTP.
        # So need to decide how to fetch the data based on the date.
        if int(self.day[:4]) >= 2017:
            # given day is 2017 or later --> fetch data by FTP
            self.ftp_noaa()
        else:
            # Given day is 2016 or earlier --> fetch data by https
            # If the file is NOT in the NOAA_CACHE_FOLDER then we need to
            # fetch it first then read line by line to grab the data
            # from the expected day
            file_path = self.http_ngdc()
            with open(file_path, "rt", encoding="utf-8") as fin:
                for line in fin:
                    fields = line.split()
                    # compare YYMMDD only
                    if fields and fields[0][5:11] == self.day[2:]:
                        # two line formats:
                        # 31777151031  0835 0841 0839 N05E57 C 17    G15  3.6E-04 12443 151104.6
                        # 31777151031  1015 1029 1022  C 15    G15  1.0E-03
                        if len(fields) == 11:
                            self.XRAlist.append((
                                fields[4],
                                self.t_stamp(fields[1]),  # beg time
                                self.t_stamp(fields[2]),  # highest time,
                                self.t_stamp(fields[3]),  # end time,
                                fields[5]+fields[6][0]+'.'+fields[6][1]))
                        elif len(fields) == 8:
                            self.XRAlist.append((
                                "None",
                                self.t_stamp(fields[1]),  # beg time
                                self.t_stamp(fields[2]),  # highest time,
                                self.t_stamp(fields[3]),  # end time,
                                fields[4]+fields[5][0]+'.'+fields[5][1]))
                        else:
                            print("Please check this line format:")
                            print(line)

    def t_stamp(self, HHMM):
        """ Convert HHMM string to datetime object."""
        # "201501311702" -> datetime(2015, 1, 31, 17, 2)
        return datetime.strptime(self.day + HHMM, "%Y%m%d%H%M")

    def http_ngdc(self):
        """
        Get the file for a past year from HTTP ngdc if not already saved.

        Return the full path of the data file
        """
        file_name = "goes-xrs-report_{}.txt" \
            .format(self.day[:4]) \
            if self.day[:4] != "2015" \
            else "goes-xrs-report_2015_modifiedreplacedmissingrows.txt"

        folder = script_relative_to_cwd_relative(NOAA_CACHE_FOLDER)

        # create NOAA_CACHE_FOLDER if it does not exist
        if not path.isdir(folder):
            try:
                os.mkdir(folder)
            except FileExistsError as err:
                sys.exit(f"'{folder}: {err}")
            except FileNotFoundError as err:
                sys.exit(f"'{folder}: {err}")
            except OSError as err:
                sys.exit(f"'{folder}: {err}")

        file_path = path.join(folder, file_name)
        url = path.join(self.ngdc_url, file_name)
        if not path.isfile(file_path):
            try:
                txt = urllib.request.urlopen(url).read().decode()
            except (urllib.error.HTTPError, urllib.error.URLError) as err:
                print(f"Cannot retrieve the file {file_name} from URL: {url}")
                print(f"Error: {err}\n")
            else:
                with open(file_path, "wt", encoding="utf-8") as fout:
                    fout.write(txt)
        return file_path

    def ftp_noaa(self):
        """
        Get the XRA data from NOAA website.

          (Used to draw corresponding lines on the plot)
          Returns the list of XRA events as
          [(eventName, BeginTime, MaxTime, EndTime, Particulars), ...]
          from the line:
          1000 +   1748 1752 1755  G15 5 XRA  1-8A M1.0 2.1E-03 2443
        """
        # ftp://ftp.swpc.noaa.gov/pub/indices/events/20141030events.txt
        noaa_url = f"ftp://ftp.swpc.noaa.gov/pub/indices/events/{self.day}events.txt"

        response, self.XRAlist = None, []
        try:
            response = urllib.request.urlopen(noaa_url)
        except (urllib.error.HTTPError, urllib.error.URLError) as err:
            print(f"Cannot retrieve the file: '{self.day}events.txt'")
            print("from URL:", noaa_url)
            print(err, "\n")
        else:
            for webline in response.read().splitlines():

                # cast bytes to str then split
                fields = str(webline, 'utf-8').split()

                if len(fields) >= 9 and not fields[0].startswith("#"):
                    if fields[1] == '+':
                        fields.remove('+')

                    # maybe other event types could be of interrest
                    if fields[6] in ('XRA',):
                        # msg = fields[0] + " "     # eventName
                        # msg += fields[1] + " "    # BeginTime
                        # msg += fields[2] + " "    # MaxTime
                        # msg += fields[3] + " "    # EndTime
                        # msg += fields[8]          # Particulars
                        try:
                            # 'try' necessary as few occurences of
                            # --:-- instead of HH:MM exist
                            btime = self.t_stamp(fields[1])
                        except Exception:
                            pass
                        try:
                            mtime = self.t_stamp(fields[2])
                        except Exception:
                            mtime = btime
                        try:
                            etime = self.t_stamp(fields[3])
                        except Exception:
                            etime = mtime
                        self.XRAlist.append((fields[0], btime, mtime, etime,
                                             fields[8]))  # as a tuple

    def print_XRAlist(self):
        """Print the XRA list in a readable format."""
        for eventName, BeginTime, MaxTime, EndTime, Particulars \
                in self.XRAlist:
            print(eventName, BeginTime, MaxTime, EndTime, Particulars)


# Run some test cases
if __name__ == '__main__':

    test_list = ["20140104",
                 "20170104",
                 "20201211",
                 "20250529",
                 datetime(2023, 10, 1, 12, 0),
                 datetime(2023, 10, 1, 12, 0, tzinfo=timezone.utc),
                 date(2023, 10, 1),
                 "2023123a"]  # this one should throw an exception


    print("NOAA_flares test cases")
    print("eventName, BeginTime, MaxTime, EndTime, Particulars")
    for test in test_list:
        try:
            flare = NOAA_flares(test)
            print(flare.day, "\n", flare.print_XRAlist(), "\n")
        except Exception as e:
            print(f"Error processing {test}: {e}\n")

    print("End of NOAA_flares test cases\n")
