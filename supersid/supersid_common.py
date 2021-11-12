import os.path
import argparse


def exist_file(x):
    """Check for argparse that file exists but does not open it."""
    if not os.path.isfile(x):
        raise argparse.ArgumentTypeError("{0} does not exist".format(x))
    return x
