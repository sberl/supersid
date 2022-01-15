#!/usr/bin/env python3
"""Config parses a supersid's .cfg file.

Parameter access: all keys are forced to lowercase
  - for parameters: config['site_name'], config['longitude'], etc...
  - for stations: config.stations[i] is a triplet:(call_sign, frequency, color)

Note: len(config.stations) == config['number_of_stations'] - sanity check -
"""
#
# Eric Gibert
#
#   Change Log:
#   20140816:
#   - define CONSTANTS to ensure universal usage
#   20150801:
#   - add the [FTP] section
#
import sys
import os.path
import configparser
import argparse
from supersid_common import script_relative_to_cwd_relative, exist_file

# constant for 'log_type'
FILTERED, RAW = 'filtered', 'raw'

# constants for mandatory station parameters
CALL_SIGN, FREQUENCY, COLOR = 'call_sign', 'frequency', 'color'

# constants for optional station parameters
CHANNEL = 'channel'

# constant for 'log_format'
SID_FORMAT, SUPERSID_FORMAT = 'sid_format', 'supersid_format'

# constant for 'log_format' with 5 decimals timestamp
SID_EXTENDED, SUPERSID_EXTENDED = 'sid_extended', 'supersid_extended'

# constant for 'log_format'
BOTH = 'both'                    # combines 'sid_format', 'supersid_format'
BOTH_EXTENDED = 'both_extended'  # combines 'sid_extended', 'supersid_extended'

# constants for alsaaudio 'Format'
S16_LE, S24_3LE, S32_LE = 'S16_LE', 'S24_3LE', 'S32_LE'

# the default configuration path, can be overridden on command line
CONFIG_FILE_NAME = script_relative_to_cwd_relative("../Config/supersid.cfg")


class Config(dict):
    """Dictionary containing the key/values pair read from a .cfg file."""

    def __init__(self, filename):
        """Read the given .cfg file or tries to find one.

        Config file is formatted as a .ini windows file
        All its key/values pairs are stored as a dictionary (self)
        :param filename: superSID .cfg file
        :return: nothing
        """
        self.version = "1.4 20150801"
        dict.__init__(self)         # Config objects are dictionaries
        self.config_ok = True       # Parsing success/failure
        self.config_err = ""        # Parsing failure error message
        config_parser = configparser.ConfigParser()

        self.filenames = config_parser.read(filename)

        if len(self.filenames) == 0:
            self.config_ok = False
            self.config_err = "Cannot find configuration file: " + filename
            return

        # Each section (dictionary entry) matches a list of parameters
        # each parameter has:
        # - a key description
        # - a type for cast
        # - a default value or None if mandatory

        sections = {
            'PARAMETERS': (
                ####################
                # optional entries #
                ####################

                # yes/no to save every hours
                ('hourly_save', str, "no"),

                # data path configuration by the user
                ('data_path', str, "../Data/"),

                # SUPERSID_EXTENDED (default)
                # suitable for automatic FTP upload
                ('log_format', str, SUPERSID_EXTENDED),

                # Server, Client, Standalone (default)
                ('mode', str, 'Standalone'),

                # text, tk (default)
                ('viewer', str, 'tk'),

                # beta_wing for sidfile.filter_buffer()
                ('bema_wing', int, 6),

                # paper size of the images, one of A3, A4, A5, Legal, Letter
                ('paper_size', str, 'A4'),

                # min value for the y axis of the psd graph
                # 'NaN' means automatic scaling
                ('psd_min', float, float('NaN')),

                # max value for the y axis of the psd graph
                # 'NaN' means automatic scaling
                ('psd_max', float, float('NaN')),

                # number of ticks for the y axis of the psd graph
                # 0 means automatic ticks
                ('psd_ticks', int, 0),

                #####################
                # mandatory entries #
                #####################

                # email of the SuperSID owner
                ('contact', str, None),
                ('site_name', str, None),
                ('longitude', str, None),
                ('latitude', str, None),
                ('utc_offset', str, None),
                ('time_zone',  str, None),
                ('monitor_id', str, None),
                ('log_type',  str, None),           # 'filtered' or 'raw'
                ('audio_sampling_rate', int, None),
                ('log_interval', int, None),
                ('number_of_stations', int, None),
                ('scaling_factor', float, None),
            ),

            'Capture': (
                # audio module: alsaaudio, sounddevice, pyaudio
                ("Audio", str, 'alsaaudio'),

                # alsaaudio, sounddevice, pyaudio: Device name for capture
                ("Device", str, 'plughw:CARD=Generic,DEV=0'),

                # alsaaudio: obsolete
                # (all audio modules are using fully qualified Device names)
                ("Card", str, ''),

                # alsaaudio: period size for capture
                ("PeriodSize", int, 1024),

                # alsaaudio: format S16_LE, S24_3LE, S32_LE
                ("Format", str, 'S16_LE'),

                # alsaaudio: number of channels to be captured
                # default 1, optional 2
                ("Channels", int, 1),
            ),

            'Linux': (                              # obsolete
                ("Audio", str, 'alsaaudio'),        # obsolete
                ("Card", str, ''),                  # obsolete
                ("PeriodSize", int, 1024),          # obsolete
            ),

            'Email': (
                # sender email
                ("from_mail", str, ""),

                # your email server (SMPT)
                ("email_server", str, ""),

                # your email server's port (SMPT)
                ("email_port", str, ""),

                # your email server requires TLS yes/no
                ("email_tls", str, "no"),

                # if your server requires a login
                ("email_login", str, ""),

                # if your server requires a password
                ("email_password", str, ""),
            ),

            'FTP': (
                # yes/no: to upload the file to the remote FTP server
                ('automatic_upload',  str, "no"),

                # address of the server like sid-ftp.stanford.edu
                ('ftp_server',  str, ""),

                # remote target directory to write the files
                ('ftp_directory', str, ""),

                # local tmp folder to generate files before upload
                ('local_tmp', str, ""),

                # list of stations to upload (sub-set of [stations])
                ('call_signs', str, ""),
            ),
        }   # End of sections

        if sys.platform.startswith('win32'):
            sections['Capture'] = (
                # audio module: sounddevice, pyaudio
                ("Audio", str, 'sounddevice'),

                # sounddevice, pyaudio: Device name for capture
                ("Device", str, 'MME: Microsoft Sound Mapper - Input'),

                # alsaaudio: format S16_LE, S24_3LE, S32_LE
                ("Format", str, 'S16_LE'),

                # alsaaudio: number of channels to be captured
                # default 1, optional 2
                ("Channels", int, 1),
            )

        self.sectionfound = set()
        for section, fields in sections.items():
            # go thru all the current section's fields
            for pkey, pcast, pdefault in fields:
                try:
                    self[pkey] = pcast(config_parser.get(section, pkey))
                except ValueError:
                    self.config_ok = False
                    self.config_err = "'%s' is not of the type %s in " \
                        "'supersid.cfg'. Please check." % (pkey, pcast)
                    return
                except configparser.NoSectionError:
                    # it's ok: some sections are optional
                    pass
                except configparser.NoOptionError:
                    if pdefault is None:  # missing mandatory parameter
                        self.config_ok = False
                        self.config_err = "'"+pkey+"' is not found in '%s'. " \
                            "Please check." % filename
                        return
                    else:  # optional, assign default
                        self.setdefault(pkey, pdefault)
                else:
                    self.sectionfound.add(section)

        if "Linux" in self.sectionfound:
            print("\n*** WARNING***\nSection [Linux] is obsolete.")
            print("Please replace it by [Capture] in your .cfg files.\n")

        # Getting the stations parameters
        self.stations = []  # now defined as a list of dictionaries

        for i in range(self['number_of_stations']):
            section = "STATION_" + str(i+1)
            tmpDict = {}
            try:
                for parameter in (CALL_SIGN, FREQUENCY, COLOR, CHANNEL):
                    if parameter == CHANNEL:
                        tmpDict[parameter] = \
                            config_parser.getint(section, parameter)
                    else:
                        tmpDict[parameter] = \
                            config_parser.get(section, parameter)
                self.stations.append(tmpDict)
            except configparser.NoSectionError:
                self.config_ok = False
                self.config_err = section + \
                    " section is expected but missing from the config file."
                return
            except configparser.NoOptionError:
                if CHANNEL == parameter:
                    tmpDict[parameter] = 0  # default is 0, the left channel
                    self.stations.append(tmpDict)
                else:
                    self.config_ok = False
                    self.config_err = section + \
                        " does not have the 3 mandatory parameters in the " \
                        "config file. Please check."
                    return
            else:
                self.sectionfound.add(section)

    def supersid_check(self):
        """Perform sanity checks when a .cfg file is read by 'supersid.py'.

        Verifies that all mandatory sections were read.
        Extend the keys with some other values for easier access.
        """
        if not self.config_ok:
            return

        for mandatory_section in ('PARAMETERS',):
            if mandatory_section not in self.sectionfound:
                self.config_ok = False
                self.config_err = mandatory_section + \
                    " section is mandatory but missing from the .cfg file."
                return

        # sanity check: as many Stations were read as
        # announced by 'number_of_stations' (now section independent)
        if self['number_of_stations'] != len(self.stations):
            self.config_ok = False
            self.config_err = "'number_of_stations' does not match STATIONS " \
                "found in supersid.cfg. Please check."
            return

        for i, station in enumerate(self.stations):
            if ((station[CHANNEL] < 0) or
                    (station[CHANNEL] >= self['Channels'])):
                self.config_ok = False
                self.config_err = \
                    "[STATION_{}] {}={} must be >= 0 and < 'Channels'={}." \
                    .format(i, CHANNEL, station[CHANNEL], self['Channels'])
                return
            if ((self['audio_sampling_rate'] // 2) < int(station[FREQUENCY])):
                # configured sampling rate is below Nyquist sampling rate
                self.config_ok = False
                self.config_err = "[STATION_{}] {}={}: " \
                    "audio_sampling_rate={} must be >= {}." \
                    .format(
                        i, FREQUENCY, station[FREQUENCY],
                        self['audio_sampling_rate'], int(station[FREQUENCY])*2
                        )
                return

        if 'stations' not in self:
            self[CALL_SIGN] = ",".join([s[CALL_SIGN] for s in self.stations])
            self[FREQUENCY] = ",".join([s[FREQUENCY] for s in self.stations])

        # log_type must be lower case and one of 'filtered' or 'raw'
        self['log_type'] = self['log_type'].lower()
        if self['log_type'] not in (FILTERED, RAW):
            self.config_ok = False
            self.config_err = "'log_type' must be either 'filtered' or " \
                "'raw' in supersid.cfg. Please check."
            return

        # 'hourly_save' must be UPPER CASE
        self['hourly_save'] = self['hourly_save'].upper()
        if self['hourly_save'] not in ('YES', 'NO'):
            self.config_ok = False
            self.config_err = "'hourly_save' must be either 'YES' or 'NO' " \
                "in supersid.cfg. Please check."
            return

        # when present, 'email_tls' must be UPPER CASE
        if 'email_tls' in self:
            self['email_tls'] = self['email_tls'].upper()
            if self['email_tls'] not in ('YES', 'NO'):
                self.config_ok = False
                self.config_err = "'email_tls' must be either 'YES' or 'NO' " \
                    "in supersid.cfg. Please check."
                return

        # 'paper_size' must be UPPER CASE
        self['paper_size'] = self['paper_size'].upper()
        if self['paper_size'] not in ('A3', 'A4', 'A5', 'LEGAL', 'LETTER'):
            self.config_ok = False
            self.config_err = "'paper_size' must be one of 'A3', 'A4', " \
                "'A5', 'Legal' or 'Letter' in supersid.cfg. Please check."
            return

        # log_interval should be > 2
        if self['log_interval'] <= 2:
            self.config_ok = False
            self.config_err = "'log_interval' <= 2. Too fast! Please increase."
            return

        # check log_format
        self['log_format'] = self['log_format'].lower()
        log_formats = [
            SID_FORMAT,
            SUPERSID_FORMAT,
            SID_EXTENDED,
            SUPERSID_EXTENDED,
            BOTH,
            BOTH_EXTENDED]
        if self['log_format'] not in log_formats:
            self.config_ok = False
            self.config_err = "'log_format' must be either one of {}." \
                .format(log_formats)
            return

        # check log_format on conjunction with automatic_upload
        log_formats_for_automatic_upload = [
            SUPERSID_FORMAT,
            SUPERSID_EXTENDED,
            BOTH,
            BOTH_EXTENDED]
        if ((self['automatic_upload'] == 'yes') and
                (self['log_format'] not in log_formats_for_automatic_upload)):
            self.config_ok = False
            self.config_err = "'log_format' must be either one of {} for " \
                "'automatic_upload = yes'." \
                .format(log_formats_for_automatic_upload)
            return

        # check viewer
        self['viewer'] = self['viewer'].lower()
        if self['viewer'] not in ('text', 'tk'):
            self.config_ok = False
            self.config_err = "'viewer' must be either one of 'text', 'tk'."
            return

        # Check the 'data_path' validity
        # and create it as a Config instance property
        self['data_path'] = script_relative_to_cwd_relative(self['data_path'])\
            + os.sep
        self.data_path = self['data_path']

        # data_path must be a folder with read/write permission
        if not os.path.isdir(self.data_path):
            self.config_ok = False
            self.config_err = "'data_path' does not point to a valid " \
                "directory:\n" + self.data_path
            return
        if not os.access(self.data_path, os.R_OK | os.W_OK):
            self.config_ok = False
            self.config_err = "'data_path' must have read/write " \
                "permission:\n" + self.data_path
            return

        # when present, 'local_tmp' must be a folder with read/write access
        if 'local_tmp' in self:
            self['local_tmp'] = script_relative_to_cwd_relative(
                self['local_tmp']) + os.sep
            self.local_tmp = self['local_tmp']
            if not os.path.isdir(self.local_tmp):
                self.config_ok = False
                self.config_err = "'local_tmp' does not point to a valid " \
                    "directory:\n" + self.local_tmp
                return
            if not os.access(self.local_tmp, os.R_OK | os.W_OK):
                self.config_ok = False
                self.config_err = "'local_tmp' must have read/write " \
                    "permission:\n" + self.local_tmp
                return

        # default audio to sounddevice if not declared
        # sounddevice is available for Windows and Linux
        # and it seems to yield better results than pyaudio
        if "Audio" not in self:
            self["Audio"] = "sounddevice"

        # obsolete Card
        if 'Card' in self:
            if self['Card']:
                print("\n*** WARNING***\n'Card' is obsolete.")
                print("Please replace it by fully qualified 'Device' in "
                      "your .cfg files.\n")

        # when present, 'Format' must be one of the supported formats
        # (relevant for the format conversion in sampler.py for alsaaudio)
        if 'Format' in self:
            if self['Format'] not in [S16_LE, S24_3LE, S32_LE]:
                self.config_ok = False
                self.config_err = "'log_format' must be either one of {}." \
                    .format([S16_LE, S24_3LE, S32_LE])
                return


def readConfig(cfg_filename):
    """Read and return the configuration or terminate the program."""
    config = Config(cfg_filename)
    config.supersid_check()
    if config.config_ok:
        assert (len(config.filenames) == 1), \
            "expected exactly one configuration file name"
        print("Config file '{}' read successfully".format(config.filenames[0]))
    else:
        print("Error:", config.config_err)
        sys.exit(1)
    return config


def printConfig(config):
    """Print the configuration in a nice format."""
    assert (len(config.filenames) == 1), \
        "expected exactly one configuration file name"
    print("--- Config file " + "-"*26)
    print("\t{}".format(config.filenames[0]))
    print("--- Sections " + "-"*29)
    for section in sorted(config.sectionfound):
        print("\t{}".format(section))
    print("--- Key Value pairs " + "-"*22)
    for k, v in sorted(config.items()):
        print("\t{} = {}".format(k, v))
    print("--- Stations " + "-"*29)
    for st in cfg.stations:
        print("\t{} = {}, {} = {}, {} = {}, {} = {}".format(
            CALL_SIGN, st[CALL_SIGN],
            FREQUENCY, st[FREQUENCY],
            COLOR, st[COLOR],
            CHANNEL, st[CHANNEL]))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", dest="cfg_filename",
                        type=exist_file,
                        default=CONFIG_FILE_NAME,
                        help="Supersid configuration file")
    args = parser.parse_args()

    # read the configuration file or exit
    cfg = readConfig(args.cfg_filename)
    printConfig(cfg)
