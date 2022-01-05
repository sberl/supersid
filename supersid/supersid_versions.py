#!/usr/bin/env python3

import sys
import pkg_resources

"""
pipdeptree

matplotlib==3.4.3
  - cycler [required: >=0.10, installed: 0.10.0]
    - six [required: Any, installed: 1.16.0]
  - kiwisolver [required: >=1.0.1, installed: 1.3.1]
  - numpy [required: >=1.16, installed: 1.21.2]
  - pillow [required: >=6.2.0, installed: 8.4.0]
  - pyparsing [required: >=2.2.1, installed: 3.0.4]
  - python-dateutil [required: >=2.7, installed: 2.8.2]
    - six [required: >=1.5, installed: 1.16.0]

sounddevice==0.4.3
  - CFFI [required: >=1.0, installed: 1.15.0]
    - pycparser [required: Any, installed: 2.21]

pyephem==9.99
  - ephem [required: Any, installed: 4.1]
"""


tested_versions = {
    # matplotlib dependencies
    'matplotlib': {'versions': ['3.4.3'], 'requirement': 'mandatory'},
    'cycler': {'versions': ['0.10.0', '0.11.0'], 'requirement': 'mandatory'},
    'six': {'versions': ['1.12.0', '1.16.0'], 'requirement': 'mandatory'},
    'kiwisolver': {'versions': ['1.3.1', '1.3.2'], 'requirement': 'mandatory'},
    'numpy': {
        'versions': ['1.21.2', '1.21.3', '1.21.4+vanilla', '1.21.5'],
        'requirement': 'mandatory'},
    'pillow': {'versions': ['8.4.0'], 'requirement': 'mandatory'},
    'pyparsing': {'versions': ['2.4.7', '3.0.4'], 'requirement': 'mandatory'},
    'python-dateutil': {'versions': ['2.8.2'], 'requirement': 'mandatory'},

    # pandas dependencies
    'pandas': {'versions': ['1.3.4', '1.3.5'], 'requirement': 'mandatory'},

    # sounddevice dependencies
    'sounddevice': {'versions': ['0.4.3'], 'requirement': 'optional'},
    'CFFI': {'versions': ['1.15.0'], 'requirement': 'optional'},
    'pycparser': {'versions': ['2.21'], 'requirement': 'optional'},

    # pyephem dependencies
    'pyephem': {'versions': ['9.99'], 'requirement': 'mandatory'},
    'ephem': {'versions': ['4.1'], 'requirement': 'mandatory'},

    # standalone
    'python': {
        'versions': ['3.7.3', '3.8.12', '3.9.7'],
        'requirement': 'mandatory'},
    'pip': {
        'versions': ['21.0.1', '21.2.2', '21.3.1'],
        'requirement': 'mandatory'},
    'pyaudio': {'versions': ['0.2.11'], 'requirement': 'optional'},
    'pyalsaaudio': {'versions': ['0.9.0'], 'requirement': 'optional'},
    # import pkg_resources
    'setuptools': {
        'versions': ['40.8.0', '57.4.0', '58.0.4'],
        'requirement': 'mandatory'},

    # builtin
    'itertools': {'versions': ['builtin'], 'requirement': 'mandatory'},
    'msvcrt': {
        'versions': ['builtin'],
        'requirement': 'OS dependent (Windows)'},
    'sys': {'versions': ['builtin'], 'requirement': 'mandatory'},
    'time': {'versions': ['builtin'], 'requirement': 'mandatory'},

    # belongs to lib
    # 'argparse': {'versions': ['lib'], 'requirement': 'mandatory'},
    # 'configparser': {'versions': ['lib'], 'requirement': 'mandatory'},
    # 'datetime': {'versions': ['lib'], 'requirement': 'mandatory'},
    # 'email': {'versions': ['lib'], 'requirement': 'mandatory'},
    # 'ftplib': {'versions': ['lib'], 'requirement': 'mandatory'},
    # 'glob': {'versions': ['lib'], 'requirement': 'mandatory'},
    # 'mimetypes': {'versions': ['lib'], 'requirement': 'mandatory'},
    # 'os': {'versions': ['lib'], 'requirement': 'mandatory'},
    # 'pprint': {'versions': ['lib'], 'requirement': 'mandatory'},
    # 'smtplib': {'versions': ['lib'], 'requirement': 'mandatory'},
    # 'struct': {'versions': ['lib'], 'requirement': 'mandatory'},
    # 'termios': {'versions': ['lib'], 'requirement': 'OS dependent (*NIX)'},
    # 'threading': {'versions': ['lib'], 'requirement': 'mandatory'},
    # 'tkinter': {'versions': ['lib'], 'requirement': 'mandatory'},
    # 'tty': {'versions': ['lib'], 'requirement': 'OS dependent (*NIX)'},
    # 'urllib': {'versions': ['lib'], 'requirement': 'mandatory'},
    # 'wave': {'versions': ['lib'], 'requirement': 'mandatory'},
}


if __name__ == '__main__':
    identified_versions = {}
    for module in tested_versions:
        try:
            if module == 'python':
                identified_versions[module] = "{}.{}.{}".format(
                    sys.version_info.major,
                    sys.version_info.minor,
                    sys.version_info.micro)
            elif (module in sys.builtin_module_names):
                identified_versions[module] = 'builtin'
            else:
                identified_versions[module] = \
                    pkg_resources.get_distribution(module).version

            if identified_versions[module] in \
                    tested_versions[module]['versions']:
                print(
                    "SUCCESS: {} '{}' found version {}"
                    .format(
                        tested_versions[module]['requirement'],
                        module,
                        identified_versions[module]))
            else:
                print(
                    "WARNING: {} '{}' found version {}, expected version(s) {}"
                    .format(
                        tested_versions[module]['requirement'],
                        module,
                        identified_versions[module],
                        tested_versions[module]['versions']))
        except Exception as e:
            if 'mandatory' == tested_versions[module]['requirement']:
                print("ERROR: {} '{}' not found".format(
                    tested_versions[module]['requirement'], module))
            else:
                print("INFO: {} '{}' not found".format(
                    tested_versions[module]['requirement'], module))
