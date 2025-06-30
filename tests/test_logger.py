"""
test for supersid_logger.py
"""
import os
import sys
import glob
import shutil
import unittest
from datetime import datetime, timezone
import readchar

from test_common import script_relative_to_cwd_relative as relpath

sys.path.append(relpath(r"../src"))
from supersid_config import read_config, CONFIG_FILE_NAME, CALL_SIGN, FREQUENCY, FILTERED, RAW
from supersid_logger import Logger
from sidfile import SidFile


class CommonLoggerTests():
    """ common tests regard """
    def assert_sid_files(self, log_type, extended):
        """
        assert the sid file properties are as expected
        """
        csv_files = glob.glob(self.config["data_path"] + "*.csv")
        self.assertTrue(len(csv_files) == len(self.config.stations))
        for station in self.config.stations:
            call_sign = station["call_sign"]
            csv_file = f"{self.config['data_path']}{self.config['site_name']}"\
                       f"_{call_sign}_{self.date}.csv"
            self.assertTrue(csv_file in csv_files)
            sid_file = SidFile(csv_file)

            self.assertEqual(sid_file.is_extended, extended)
            # check sid_file.sid_params[key] in the order the keys appear in the .csv files
            self.assertEqual(sid_file.sid_params["contact"], self.config["contact"])
            self.assertEqual(sid_file.sid_params["frequency"], station["frequency"])
            self.assertEqual(sid_file.sid_params["latitude"], self.config["latitude"])
            self.assertEqual(int(sid_file.sid_params["loginterval"]), self.config["log_interval"])
            self.assertEqual(sid_file.LogInterval, self.config["log_interval"])
            self.assertEqual(sid_file.sid_params["logtype"], log_type)
            self.assertEqual(sid_file.sid_params["longitude"], self.config["longitude"])
            self.assertEqual(sid_file.sid_params["monitorid"], self.config["monitor_id"])
            self.assertEqual(sid_file.sid_params["site"], self.config["site_name"])
            self.assertEqual(sid_file.sid_params["stationid"], station["call_sign"])
            self.assertEqual(sid_file.sid_params["timezone"], self.config["time_zone"])
            self.assertEqual(sid_file.sid_params["utc_offset"], self.config["utc_offset"])
            self.assertEqual(sid_file.sid_params["utc_starttime"], self.date + " 00:00:00")

    def test__log_sid_format__default(self):
        """
        test Logger.log_sid_format()
        with default parameters (log_type=FILTERED, extended=False)
        """
        self.logger.log_sid_format(self.config.stations)
        self.assert_sid_files(log_type=FILTERED, extended=False)

    def test__log_sid_format__variations(self):
        """
        test Logger.log_sid_format()
        with variations of the named parameters (log_type=?, extended=?)
        """
        for log_type in [FILTERED, RAW]:
            for extended in [False, True]:
                self.logger.log_sid_format(
                    self.config.stations,
                    log_type=log_type,
                    extended=extended)
                self.assert_sid_files(log_type, extended)

    def assert_supersid_file(self, filename, log_type, extended):
        """
        assert the supersid file properties are as expected
        """
        csv_files = glob.glob(self.config["data_path"] + "*.csv")
        self.assertTrue(len(csv_files) == 1) # one file for all stations
        if filename:
            csv_file = filename
        else:
            csv_file = f"{self.config['data_path']}{self.config['site_name']}_{self.date}.csv"
        self.assertTrue(csv_file in csv_files)
        sid_file = SidFile(csv_file)

        call_signs = []
        frequencies = []
        for station in self.config.stations:
            call_signs.append(station["call_sign"])
            frequencies.append(station["frequency"])
        call_signs = ",".join(s for s in call_signs)
        frequencies = ",".join(s for s in frequencies)

        self.assertEqual(sid_file.is_extended, extended)
        # check sid_file.sid_params[key] in the order the keys appear in the .csv files
        self.assertEqual(sid_file.sid_params["contact"], self.config["contact"])
        self.assertEqual(sid_file.sid_params["frequencies"], frequencies)
        self.assertEqual(sid_file.sid_params["latitude"], self.config["latitude"])
        self.assertEqual(int(sid_file.sid_params["loginterval"]), self.config["log_interval"])
        self.assertEqual(sid_file.LogInterval, self.config["log_interval"])
        self.assertEqual(sid_file.sid_params["logtype"], log_type)
        self.assertEqual(sid_file.sid_params["longitude"], self.config["longitude"])
        self.assertEqual(sid_file.sid_params["monitorid"], self.config["monitor_id"])
        self.assertEqual(sid_file.sid_params["site"], self.config["site_name"])
        self.assertEqual(sid_file.sid_params["stations"], call_signs)
        self.assertEqual(sid_file.sid_params["timezone"], self.config["time_zone"])
        self.assertEqual(sid_file.sid_params["utc_offset"], self.config["utc_offset"])
        self.assertEqual(sid_file.sid_params["utc_starttime"], self.date + " 00:00:00")

    def test__log_supersid_format__default(self):
        """
        test Logger.log_supersid_format()
        with default parameters (filename='', log_type=FILTERED, extended=False)
        """
        self.logger.log_supersid_format(self.config.stations)
        self.assert_supersid_file(filename='', log_type=FILTERED, extended=False)

    def test__log_supersid_format__variations(self):
        """
        test Logger.log_supersid_format()
        with variations of the named parameters (filename='', log_type=?, extended=?)
        """
        for filename in ["", "test.csv", os.path.abspath(f"{self.config['data_path']}test.csv")]:
            for log_type in [FILTERED, RAW]:
                for extended in [False, True]:
                    csv_files = glob.glob(self.config["data_path"] + "*.csv")
                    for file in csv_files:
                        os.remove(file)
                    self.logger.log_supersid_format(
                        self.config.stations,
                        filename=filename,
                        log_type=log_type,
                        extended=extended)
                    if filename:
                        if os.path.isabs(filename):
                            rel_name = f"{self.config['data_path']}{os.path.split(filename)[-1]}"
                        else:
                            rel_name = f"{self.config['data_path']}{filename}"
                    else:
                        rel_name = filename # use empty filename as is
                    self.assert_supersid_file(
                        filename=rel_name,
                        log_type=log_type,
                        extended=extended)


class TestOneStation(unittest.TestCase, CommonLoggerTests):
    """ tests class Logger with one station in spersid.cfg """
    def setUp(self):
        """ generic setup for all tests """
        if os.path.isfile(CONFIG_FILE_NAME):
            os.remove(CONFIG_FILE_NAME)
        shutil.copy2(relpath("test_logger_1_station.cfg"), CONFIG_FILE_NAME)
        self.config = read_config(CONFIG_FILE_NAME)
        self.logger = Logger(self)
        self.date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        csv_files = glob.glob(self.config["data_path"] + "*.csv")
        for file in csv_files:
            os.remove(file)

    def test__init(self):
        """ test Logger.__init__() """
        self.assertEqual(self.config["stationid"], self.config.stations[0][CALL_SIGN])
        self.assertEqual(self.config["frequency"], self.config.stations[0][FREQUENCY])
        self.assertEqual(self.config["data_path"], relpath("../Data") + os.sep)


class TestTwoStations(unittest.TestCase, CommonLoggerTests):
    """ tests class Logger with two stations in spersid.cfg """
    def setUp(self):
        """ generic setup for all tests """
        if os.path.isfile(CONFIG_FILE_NAME):
            os.remove(CONFIG_FILE_NAME)
        shutil.copy2(relpath("test_logger_2_stations.cfg"), CONFIG_FILE_NAME)
        self.config = read_config(CONFIG_FILE_NAME)
        self.logger = Logger(self)
        self.date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        csv_files = glob.glob(self.config["data_path"] + "*.csv")
        for file in csv_files:
            os.remove(file)

    def test_init(self):
        """ test Logger.__init__() """
        self.assertEqual(self.config["stations"],
                         ",".join([s[CALL_SIGN] for s in self.config.stations]))
        self.assertEqual(self.config["frequencies"],
                         ",".join([s[FREQUENCY] for s in self.config.stations]))
        self.assertEqual(self.config["data_path"], relpath("../Data") + os.sep)


def main():
    """ the main function """
    warning = "This test will modify and/or delete the content of 'Config' and 'Data' folders.\n" \
              "It is up to you to take backups.\n" \
              "Do you want to continue (Y|n)?"
    print(warning)

    while True:
        ch = readchar.readkey().lower()
        if ch in ['y', chr(0x0D), chr(0x0A)]:
            # shutil.copy2(r"../Config/supersid.cfg", r"../Config/supersid.test_logger.bak")
            unittest.main()
            # shutil.copy2(r"../Config/supersid.test_logger.bak", r"../Config/supersid.cfg")
        elif 'n' == ch:
            sys.exit()
        else:
            print(warning)

if __name__ == '__main__':
    main()
