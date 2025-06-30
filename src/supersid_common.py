#!/usr/bin/env python3
"""
A bunch of common functions used throughout the Supersid python code
"""
import sys
import os.path
import argparse
import unicodedata
import re

def exist_file(x):
    """Check for argparse that file exists but does not open it."""
    if not os.path.isfile(x):
        raise argparse.ArgumentTypeError(f"{x} does not exist")
    return x


def script_relative_to_cwd_relative(path):
    """
    converts a path which is meant to be relative to the script into
    a path relative to the cwd
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
    # it is a relative path,
    # convert it to a relative path with respect to the script folder
    absolute_cwd = os.path.realpath(os.getcwd())
    absolute_script_path = os.path.dirname(os.path.realpath(sys.argv[0]))
    relative_path = os.path.relpath(absolute_script_path, absolute_cwd)
    return os.path.normpath(os.path.join(relative_path, path))


def slugify(value, allow_unicode=False):
    """
    Source: https://github.com/django/django/blob/master/django/utils/text.py
    Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
    dashes to single dashes. Remove characters that aren't alphanumerics,
    underscores, or hyphens. Convert to lowercase. Also strip leading and
    trailing whitespace, dashes, and underscores.
    """
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize('NFKC', value)
    else:
        value = unicodedata.normalize('NFKD', value) \
            .encode('ascii', 'ignore') \
            .decode('ascii')
    value = re.sub(r'[^\w\s-]', '.', value)
    return re.sub(r'[-\s]+', '-', value)


def is_script():
    executable = os.path.split(sys.executable)[-1].lower()
    return 'python' in os.path.splitext(executable)[0]


if __name__ == '__main__':
    if is_script():
        ext = ".py"
    else:
        ext = ".exe"

    for file in [
            f'supersid_common{ext}',
            f'./supersid_common{ext}',
            '../Config/supersid.cfg',
            "not_a_file"]:
        try:
            print(exist_file(script_relative_to_cwd_relative(file)))
        except Exception as e:
            print(e)
