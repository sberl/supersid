"""Logger class keeps track of collected data and writes it out to files.

Log Station data into 2 different formats:
    sid_format (single column with time)
    supersid (multiple columns without time),

Eric Gibert

Change tracking:
    20140816:
        - add config.CONSTANT
    20150801:
        - truncate sid_params['utc_starttime'] to 19 first chars
"""
import sys
from os import path
from time import gmtime, strftime
from sidfile import SidFile
from supersid_config import FILTERED, RAW, CALL_SIGN, FREQUENCY
from supersid_config import SID_FORMAT, SUPERSID_FORMAT


class Logger():
    """
    Open the file with in memory buffer to record the future signal readings.

    Write the file to disk upon controller's request: user choice or timing
    """

    def __init__(self, controller, read_file=None):
        """
        Create a Logger based on parameters found in the .cfg file.

        controller: (as in MVC model) instance of the supersid.SuperSID class
        read_file: optional file to read at launch if given on the command line
        :return: nothing but self
        """
        self.version = "1.4 20150801"
        self.controller = controller
        self.config = controller.config
        # first create in memory buffers
        if len(self.config.stations) == 1:
            # only one station to monitor, let's default to SID file format
            self.controller.isSuperSID = False  # TODO: What is this good for? Class SuperSid has no attribute isSuperSID.
            self.config["stationid"] = self.config.stations[0][CALL_SIGN]
            self.config["frequency"] = self.config.stations[0][FREQUENCY]
        elif len(self.config.stations) > 1:
            # more than one station to monitor, default to SuperSId file format
            self.controller.isSuperSID = True  # TODO: What is this good for? Class SuperSid has no attribute isSuperSID.
            self.config["stations"] = ",".join([s[CALL_SIGN] for s in self.config.stations])
            self.config["frequencies"] = ",".join([s[FREQUENCY] for s in self.config.stations])
        else:
            print("Error: no station to log???")
            sys.exit(5)
        self.sid_file = SidFile(sid_params=self.config)

        # Do we have a file to read from the command line by the user at launch
        if read_file:
            sid_file2 = SidFile(filename=read_file)
            if sid_file2.sid_params['logtype'] != RAW:
                print("The file type is not raw but",
                      sid_file2.sid_params['logtype'])
                answer = input(
                    "Do you still want to keep its content and continue "
                    "recording? [y/N]")
                if answer.lower() != 'y':
                    print("Abort.")
                    sys.exit(-10)
            elif (sid_file2.sid_params['utc_starttime'][:19]
                    != strftime("%Y-%m-%d 00:00:00", gmtime())):
                print("Not today's file. The file UTC_StartTime =",
                      sid_file2.sid_params['utc_starttime'])
                answer = input(
                    "Do you still want to keep its content and continue "
                    "recording? [y/N]")
                if answer.lower() != 'y':
                    print("Abort.")
                    sys.exit(-11)
            elif (sorted(sid_file2.stations)
                    != sorted([s['call_sign'] for s in self.config.stations])):
                print("Station Lists are different:",
                      sid_file2.stations, "!=",
                      [s['call_sign'] for s in self.config.stations])
                answer = input(
                    "Do you still want to keep its content and continue "
                    "recording? [y/N]")
                if answer.lower() != 'y':
                    print("Abort.")
                    sys.exit(-11)
            self.sid_file.copy_data(sid_file2)
            print("Continue recording with data from file",
                  read_file, "included.")

    def log_sid_format(self, stations, log_type=FILTERED, extended=False):
        """One file per station. By default, buffered data is filtered."""
        filenames = []
        for station in stations:
            my_filename = self.config['data_path'] \
                + self.sid_file.get_sid_filename(station['call_sign'])
            filenames.append(my_filename)
            self.sid_file.write_data_sid(station, my_filename, log_type,
                                         extended=extended,
                                         bema_wing=self.config["bema_wing"])
        return filenames

    def log_supersid_format(self, stations, filename='',
                            log_type=FILTERED, extended=False):
        """Cascade all buffers in one file."""
        my_filename = filename \
            if filename and path.isabs(filename) \
            else self.config['data_path'] \
            + (filename or self.sid_file.get_supersid_filename())
        self.sid_file.write_data_supersid(my_filename, log_type,
                                          extended=extended,
                                          bema_wing=self.config["bema_wing"])
        return [my_filename]
