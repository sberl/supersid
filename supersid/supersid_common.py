#!/usr/bin/env python3

import os.path
import argparse


def exist_file(x):
    """Check for argparse that file exists but does not open it."""
    if not os.path.isfile(x):
        raise argparse.ArgumentTypeError("{0} does not exist".format(x))
    return x


def script_relative_to_cwd_relative(path):
    """
    converts a path which is meant to be relative to the script into a path relative to the cwd
    in:
        either absolute path
        or path relative to the script
    out:
        either unmodified absolute path
        or path relative to the cwd
    """
    if os.path.isabs(path):
        # it is an absolute path, don't touch it
        return path
    else:
        # it is a relative path, convert it to a relative path with respect to teh script folder
        absolute_cwd = os.path.realpath(os.getcwd())
        absolute_script_path = os.path.dirname(os.path.realpath(__file__))
        relative_path = os.path.relpath(absolute_script_path, absolute_cwd)
        return os.path.normpath(os.path.join(relative_path, path))


if __name__ == '__main__':
    for file in ['supersid_common.py', './supersid_common.py', '../Config/supersid.cfg']:
        try:
            print(exist_file(script_relative_to_cwd_relative(file)))
        except Exception as e:
            print(e)
