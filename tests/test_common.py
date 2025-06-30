"""
common functionality for uinttest
"""

import os
import sys


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
