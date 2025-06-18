#!/usr/bin/env python3
"""
Retrieve data from NOAA regarding X-ray solar flares (GOES).

Input Parameter is date of solar observation
    Date can be specified as either a datetime object, a date object,
    or a string of the form YYYYMMDD

Optional input parameter
        noaa_cache_full_path - in case default cache location is overridden
Output:
    Returns a NOAA_flares object.
        my_flares = NOAA_flares(date)
        flare_list = my_flares.get_xra_list()
        my_flares.print_xra_list() # print out the list of flares on the day

    xra_list is a list of tuples. Each tuple represents a flare detected by GOES satellite
    Each tuple contains:
        Name of the event
        Date of beginning of event
        UTC time of beginning of event
        Date of max x-ray flux
        Time of max x-ray flux
        Date of end of event
        Time of end of event
        Classification of strength of the event (A, B, C, M, X, etc.)

  (Used to draw corresponding lines on the plot)
          Returns the list of XRA events as
          [(eventName, BeginTime, MaxTime, EndTime, Particulars), ...]
          from the line:
          1000 +   1748 1752 1755  G15 5 XRA  1-8A M1.0 2.1E-03 2443

    If the date is from 2015-06-29 to the present (as of 2025-06-16), it is
    retrieved via FTP. Each file has 1 day of flare data and can be found at
    ftp://ftp.swpc.noaa.gov/pub/indices/events/{YYYYMMDD}events.txt
    where {YYYYMMDD} is replaced by 4-digit year, 2-digit month and 2-digit day.

    For dates before 2015-06-29 we must download a compressed archive file that
    contains a complete year of flare data. This file is also available via FTP.
    The URL is ftp://ftp.swpc.noaa.gov/pub/warehouse/{year}/{year}_events.tar.gz
    Once the file is downloaded, it is uncompressed into a directory hierarchy.
    In that hierarchy, the path to the daily file is ./YYYY_events/YYYYMMDDevents.txt

    These files all have the same format as described in
    ftp://ftp.swpc.noaa.gov/pub/indices/events/README

    It is not clear if and when any of this is going to change.

ftp://ftp.swpc.noaa.gov/pub/indices/events/20150629events.txt
https://www.ngdc.noaa.gov/stp/space-weather/solar-data/solar-features/solar-flares/x-rays/goes/xrs/goes-xrs-report_2014.txt
"""

import urllib.request
import urllib.error
import ftplib
import os
from os import path
import time
from datetime import datetime, date, timezone
from supersid_common import script_relative_to_cwd_relative


class NOAA_flares:
    """This object carries a list of all x-ray flare events of a given day."""
    def __init__(self, day,
                 noaa_cache_path=None):
        """ Initialize the NOAA flares object.
            Input parameter day can be either:
            - a datatime object
            - or a string of the form YYYYMMDD
            noaa_cache_path can be used if the system configuration has overridden
            the default cache location at ../Private

        """

        # xra_list is a list of tuples.
        # Each contains:
        # (event_number, begin_time, max_time, end_time, flare_strength)
        self.xra_list = [] # List of tuples

        if noaa_cache_path is None:
            self.cache_path = script_relative_to_cwd_relative(path.join("..", "Private"))
        else:
            self.cache_path = noaa_cache_path

        # create cache folder if it does not exist
        if not path.isdir(self.cache_path):
            try:
                os.mkdir(self.cache_path)
            except OSError:
                print("Unable to create folder:", self.cache_path)
        self.manage_xre_cache()

        if isinstance(day, str):
            self.day = day[:8]  # limit to YYYYMMDD
        elif isinstance(day, (datetime, date)):
            self.day = day.strftime('%Y%m%d')
        else:
            raise TypeError(
                "Unknown date format - expecting str 'YYYYMMDD' or "
                "datetime/date")

        # Code beyond this point assumes self.day is a string in 'YYYYMMDD' format
        if len(self.day) != 8 or not self.day.isdigit():
            raise ValueError("day must be a string in 'YYYYMMDD' format")

        # Starting in year 2017, NOAA makes the data available via FTP.
        # Earlier year data is available via HTTP.
        # Decide how to fetch the data based on the date.
        if int(self.day[:4]) >= 2017:
            # given day is 2017 or later --> fetch data by FTP
            file = self.ftp_fetch_noaa()
            self.parse_noaa_event_file(file)
        else:
            # Given day is 2016 or earlier --> fetch data by https
            # If the file is NOT in the self.cache_path directory then we need to
            # fetch it first then read line by line to grab the data
            # from the expected day
            file_path = self.http_fetch_ngdc()
            self.parse_ngdc_file(file_path)

    def parse_ngdc_file(self, file_path):
        """ Parse the goes-xrs-report file retrieved from website
            local_file is a path to the file in the Private folder
            Populates self.xra_list with xra data
        """
        try:
            with open(file_path, "rt", encoding="utf-8") as fin:
                for line in fin:
                    fields = line.split()
                    # compare YYMMDD only
                    if fields and fields[0][5:11] == self.day[2:]:
                        # two line formats:
                        # 31777151031  0835 0841 0839 N05E57 C 17    G15  3.6E-04 12443 151104.6
                        # 31777151031  1015 1029 1022  C 15    G15  1.0E-03
                        if len(fields) == 11:
                            self.xra_list.append((
                                fields[4],
                                self.t_stamp(fields[1]),  # beg time
                                self.t_stamp(fields[2]),  # highest time,
                                self.t_stamp(fields[3]),  # end time,
                                fields[5]+fields[6][0]+'.'+fields[6][1]))
                        elif len(fields) == 8:
                            self.xra_list.append((
                                "None",
                                self.t_stamp(fields[1]),  # beg time
                                self.t_stamp(fields[2]),  # highest time,
                                self.t_stamp(fields[3]),  # end time,
                                fields[4]+fields[5][0]+'.'+fields[5][1]))
                        else:
                            print("Please check this line format:")
                            print(line)
        except FileNotFoundError:
            print("File not found")

    def t_stamp(self, hhmm):
        """ Convert HHMM string to datetime object."""
        # "201501311702" -> datetime(2015, 1, 31, 17, 2)
        return datetime.strptime(self.day + hhmm, "%Y%m%d%H%M")

    def http_fetch_ngdc(self):
        """
        Get the file for the year from HTTP ngdc if not already saved.

        Return the full path of the data file
        """

        ngdc_url = ("https://www.ngdc.noaa.gov/stp/space-weather/"
                    "solar-data/solar-features/solar-flares/x-rays/goes/xrs/")

        if self.day[:4] != "2015":
            file_name = f"goes-xrs-report_{self.day[:4]}.txt"
        else:
            file_name = "goes-xrs-report_2015_modifiedreplacedmissingrows.txt"

        folder = self.cache_path
        file_path = path.join(folder, file_name)
        url = path.join(ngdc_url, file_name)
        if path.isfile(file_path):
            print(f"local file {file_name} already exists")
        else:
            print(f"downloading {file_name} from www.ngdc.noaa.gov")
            try:
                txt = urllib.request.urlopen(url).read().decode()
            except (urllib.error.HTTPError, urllib.error.URLError) as err:
                print(f"Cannot retrieve the file {file_name} from URL: {url}")
                print(f"Error: {err}\n")
            else:
                with open(file_path, "wt", encoding="utf-8") as fout:
                    fout.write(txt)
        return file_path

    def ftp_fetch_noaa(self):
        """
        Get the XRA data from NOAA website via FTP
        This method will get data from 2015-06-29 up to
        the present (last checked 2025-06-16)
        Older data can be retrieved. Those files are in compressed
        archive files containing an entire year of data.
        """
        # ftp://ftp.swpc.noaa.gov/pub/indices/events/20141030events.txt
        # noaa_url = f"ftp://ftp.swpc.noaa.gov/pub/indices/events/{self.day}events.txt"

        noaa_ftp_host = "ftp.swpc.noaa.gov"
        noaa_ftp_path = f"pub/indices/events/{self.day}events.txt"
        noaa_ftp_file = f"{self.day}events.txt"

        local_folder = self.cache_path
        local_file = path.join(local_folder, noaa_ftp_file)
        if path.isfile(local_file):
            print(f"local file {local_file} already exists")
        else:
            print(f"downloading {local_file} from {noaa_ftp_host}")
            try:
                ftp = ftplib.FTP(noaa_ftp_host)
                ftp.login(user='anonymous', passwd='example@example.com')
                ftp_command = f"RETR {noaa_ftp_path}"
                with open(local_file, 'wb') as local_fd:
                    ftp.retrbinary(ftp_command, local_fd.write)
                ftp.quit()
            except ftplib.all_errors as err:
                print(f"Can't retrieve FTP file {noaa_ftp_host}/{noaa_ftp_path}: {err}")
        return local_file

    def parse_noaa_event_file(self,local_file):
        """ Parse the NOAA event file retrieved from website
            local_file is a path to the file in the Private folder
            Populates self.xra_list with xra data
        """
        # At this point the file is in Private cache directory.
        try:
            with open(local_file, "rt", encoding="utf-8") as goes_data:
                for line in goes_data:
                    if (line[0] != "#") and (line[0] != ":"): #ignore comment lines
                        fields = line.split()
                        if len(fields) >= 9:
                            if fields[1] == '+':
                                fields.remove('+')
                            if fields[6] in ('XRA',):
                                # fields[0] eventName
                                # fields[1] BeginTime
                                # fields[2] MaxTime
                                # fields[3] EndTime
                                # fields[8] Particulars
                                try:
                                    # 'try' necessary as few occurrences of
                                    # --:-- instead of HH:MM exist
                                    begin_time = self.t_stamp(fields[1])
                                except (ValueError,TypeError,AttributeError):
                                    pass
                                try:
                                    max_time = self.t_stamp(fields[2])
                                except (ValueError,TypeError,AttributeError):
                                    max_time = begin_time
                                try:
                                    end_time = self.t_stamp(fields[3])
                                except (ValueError,TypeError,AttributeError):
                                    end_time = max_time
                                self.xra_list.append((fields[0],
                                                      begin_time,
                                                      max_time,
                                                      end_time,
                                                      fields[8]))
        except FileNotFoundError:
            print(f"File {local_file} not found")


    def get_xra_list(self):
        """Return the list of tuples that contain flare data"""
        return self.xra_list


    def print_xra_list(self):
        """Print the XRA list in a readable format."""
        for event_name, begin_time, max_time, end_time, particulars in self.xra_list:
            print(event_name, begin_time, max_time, end_time, particulars)

    def manage_xre_cache(self):
        """ Delete certain files from the cache folder
            Recent event files are updated as new data comes in for about 3 days.
            So, if the files is more than 1 hour old, and less than 3 days old,
            it should be deleted so that a newer, more recent version will be
            retrieved.
        """

        print(f"Purging some files from {self.cache_path}")
        current_time = datetime.now()

        # Don't delete the README
        for filename in os.listdir(self.cache_path):
            if filename == "README.md":
                continue

            # Don't delete a subdirectory
            file_path = os.path.join(self.cache_path, filename)
            if os.path.isdir(file_path):
                continue

            # Don't delete if name is more than 4 days ago
            year_string = filename[:4]
            month_string = filename[4:6]
            day_string = filename[6:8]
            try:
                file_date = datetime(year=int(year_string),
                                     month=int(month_string),
                                     day=int(day_string))
            except ValueError:
                # Probably a goes-xrs-report which is always more than 3 days old
                #print(f"Can't determine file date for {filename}")
                continue
            #print(f"{filename} day: {day_string} month: {month_string} year: {year_string} "
            #        f"filedate: {file_date}")
            file_age = current_time - file_date
            #print(f"{file_age.days} days old")
            if file_age.days > 4:
                #print(f"File {filename} is greater than 4 days old")
                continue

            # Don't delete file if downloaded less than an hour ago
            modification_timestamp = os.path.getmtime(file_path)
            modification_time = datetime.fromtimestamp(modification_timestamp)
            current_time = datetime.now()
            file_age = current_time - modification_time
            #print(f"{file_path} is {file_age.seconds} seconds old")
            if file_age.seconds < 3600: # seconds is 1 hour
                #print(f"{file_path} is less than 1 hour  old")
                continue

            try:
                os.remove(file_path)
                print(f"Deleted: {file_path}")
            except OSError as err:
                print(f"Error deleting {file_path}: {err}")
        print("Done purging cache")

# Run some test cases
if __name__ == '__main__':

    test_list = ["20140104",
                  "20130525", # this one should download the goes-xrs report
                  "20130525", # should be in the cache so faster
                  "20170104",
                  "20201211",
                  "20250529",
                 # # next 3 have the same date and file so 1st
                 # # should download, 2nd and 3rd use cache
                  datetime(2023, 10, 1, 12, 0),
                  datetime(2023, 10, 1, 12, 0, tzinfo=timezone.utc),
                  date(2023, 10, 1),

                 datetime.now(timezone.utc),
                 "foobar"]  # invalid input - throw exception

    def clear_xra_cache():
        """ Utility to clear the XRA cache before running tests"""
        directory_path = script_relative_to_cwd_relative(path.join("..", "Private"))
        if not os.path.isdir(directory_path):
            print(f"Directory '{directory_path}' does not exist.")
        for filename in os.listdir(directory_path):
            if filename != "README.md":
                file_path = os.path.join(directory_path, filename)
                if os.path.isfile(file_path):  # Check if it's a file (not a subdirectory)
                    try:
                        os.remove(file_path)
                        print(f"Deleted: {file_path}")
                    except OSError as err:
                        print(f"Error deleting {file_path}: {err}")

    #clear_xra_cache()
    for test in test_list:
        try:
            t_start = time.time()
            print(f"Test for date {test}")
            flare = NOAA_flares(test)
            flare_list = flare.get_xra_list()
            flare.print_xra_list()
            print(f"querying {flare.day} took {time.time() - t_start:0.3f} seconds\n")
        except Exception as e:
            print(f"Error processing {test}: {e}\n")

    print("End of NOAA_flares test cases\n")
