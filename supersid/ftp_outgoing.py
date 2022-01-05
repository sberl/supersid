#!/usr/bin/env python3

"""
Send data to FTP server from local_tmp ftp_directory.

Any .csv files in the local_tmp directory will be sent to the FTP server.
Once they are successfully transfered, the file will be deleted.
The idea is that this program will run periodically (hourly?), and make sure
that all the files are transfered, even if there are Internet or power outages.

Name: ftp_outgoing.py
Author: Steve Berl

Created: 2022-01-03

Module can be run from the command line, or invoked programmatically
Command line argument:

-c|--config supersid.cfg : the configuration file for its [FTP]
   and [PARAMETERS] sections

"""

import sys
import os
import ftplib
from socket import gaierror
import argparse
from supersid_common import exist_file
from config import readConfig, CONFIG_FILE_NAME


def create_file_list(config):
    """Create a list of files to send to FTP server."""
    print("local_tmp: ", config.get('local_tmp'))
    print("Current working directory before", os.getcwd())

    try:
        os.chdir(config.get('local_tmp'))
    except OSError:
        print("Something wrong with specified directory. Exception- ")
        print(sys.exc_info())

    print("Current working directory after", os.getcwd())

    try:
        file_list = [f for f in os.listdir(os.curdir) if (
            os.path.isfile(f)
            & f.endswith('.csv')
            & f.startswith(config.get('site_name')))]
    except OSError:
        print("Something wrong with specified directory. Exception- ")
        print(sys.exc_info())
        sys.exit(1)

    for file in file_list:
        print(file)

    return file_list


def ftp_send(config, files_list):
    """
    FTP the files to the server destination specified in the config.

    It is assumed that the current working directory is the directory
    containing the files in the list.
    """
    print(files_list)
    print("Opening FTP session with", config.get('ftp_server'))

    try:
        ftp = ftplib.FTP(config.get('ftp_server'))
    except gaierror as ex:
        print(ex)
        print("Check ftp_server in .cfg file")
        sys.exit(1)

    ftp.login("anonymous", config.get('contact'))
    ftp.cwd(config.get('ftp_directory'))
    print("putting files to ", config.get('ftp_directory'))
    # ftp.dir(data.append)
    for file_name in files_list:
        print("Sending {}".format(file_name))
        with open(file_name, 'r', encoding='ascii') as file_desc:
            try:
                ftp.storlines("STOR " + file_name, file_desc)
                # if sucess, delete the files
                print("Deleting: ", file_name)
            except ftplib.all_errors as err:
                print("Error sending", file_name, ":", err)
                # Dont delete file if there is an error.
                # We will try again another time.

    ftp.quit()
    print("FTP session closed.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Upload data files to server")
    parser.add_argument("-c", "--config", dest="cfg_filename",
                        type=exist_file,
                        default=CONFIG_FILE_NAME,
                        help="Supersid configuration file")

    args = parser.parse_args()

    # read the configuration file or exit
    cfg = readConfig(args.cfg_filename)
    # readConfig will check if local_tmp is configured and points to a
    # directory. It does not check if the directory is writeable.

    files_to_send = create_file_list(cfg)

    ftp_send(cfg, files_to_send)

    print("Exit with no errors")
    sys.exit(0)
