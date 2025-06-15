#!/usr/bin/env python3

import sys
from importlib.metadata import version

"""
example for Python 3.13.5M Python 3.9.12 has two more dependencies for matplotlib

pipdeptree

matplotlib==3.10.3
├── contourpy [required: >=1.0.1, installed: 1.3.2]
│   └── numpy [required: >=1.23, installed: 2.3.0]
├── cycler [required: >=0.10, installed: 0.12.1]
├── fonttools [required: >=4.22.0, installed: 4.58.4]
├── kiwisolver [required: >=1.3.1, installed: 1.4.8]
├── numpy [required: >=1.23, installed: 2.3.0]
├── packaging [required: >=20.0, installed: 25.0]
├── pillow [required: >=8, installed: 11.2.1]
├── pyparsing [required: >=2.3.1, installed: 3.2.3]
└── python-dateutil [required: >=2.7, installed: 2.9.0.post0]
    └── six [required: >=1.5, installed: 1.17.0]

pandas==2.3.0
├── numpy [required: >=1.26.0, installed: 2.3.0]
├── python-dateutil [required: >=2.8.2, installed: 2.9.0.post0]
│   └── six [required: >=1.5, installed: 1.17.0]
├── pytz [required: >=2020.1, installed: 2025.2]
└── tzdata [required: >=2022.7, installed: 2025.2]

pyephem==9.99
└── ephem [required: Any, installed: 4.2]

sounddevice==0.5.2
└── cffi [required: >=1.0, installed: 1.17.1]
    └── pycparser [required: Any, installed: 2.22]
"""

# belongs to lib, version cannot be verified
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

tested_versions = {
    'Python 3.9.12': { # Windows 11
        # matplotlib dependencies
        'matplotlib': {'versions': ['3.9.4'], 'requirement': 'mandatory'},
        'contourpy': {'versions': ['1.3.0'], 'requirement': 'mandatory'},
        'numpy': {'versions': ['1.23.5'], 'requirement': 'mandatory'},
        'cycler': {'versions': ['0.12.1'], 'requirement': 'mandatory'},
        'fonttools': {'versions': ['4.58.4'], 'requirement': 'mandatory'},
        'kiwisolver': {'versions': ['1.4.7'], 'requirement': 'mandatory'},
        'packaging': {'versions': ['25.0'], 'requirement': 'mandatory'},
        'pillow': {'versions': ['11.2.1'], 'requirement': 'mandatory'},
        'pyparsing': {'versions': ['3.2.3'], 'requirement': 'mandatory'},
        'python-dateutil': {'versions': ['2.9.0.post0'], 'requirement': 'mandatory'},
        'six': {'versions': ['1.17.0'], 'requirement': 'mandatory'},
        'importlib_resources': {'versions': ['6.5.2'], 'requirement': 'mandatory'},
        'zipp': {'versions': ['3.23.0'], 'requirement': 'mandatory'},

        # pandas dependencies
        'pandas': {'versions': ['2.1.4'], 'requirement': 'mandatory'},
        'pytz': {'versions': ['2025.2'], 'requirement': 'mandatory'},
        'tzdata': {'versions': ['2025.2'], 'requirement': 'mandatory'},

        # sounddevice dependencies
        'sounddevice': {'versions': ['0.5.2'], 'requirement': 'optional'},
        'cffi': {'versions': ['1.17.1'], 'requirement': 'optional'},
        'pycparser': {'versions': ['2.22'], 'requirement': 'optional'},

        # pyephem dependencies
        'pyephem': {'versions': ['9.99'], 'requirement': 'mandatory'},
        'ephem': {'versions': ['4.2'], 'requirement': 'mandatory'},

        # standalone
        'pip': {'versions': ['25.1.1'], 'requirement': 'mandatory'},
        'pyaudio': {'versions': ['0.2.14'], 'requirement': 'optional'},
        'pyalsaaudio': {'versions': ['0.9.0'], 'requirement': 'optional'},

        # builtin
        'itertools': {'versions': ['builtin'], 'requirement': 'mandatory'},
        'msvcrt': {
            'versions': ['builtin'],
            'requirement': 'OS dependent (Windows)'},
        'sys': {'versions': ['builtin'], 'requirement': 'mandatory'},
        'time': {'versions': ['builtin'], 'requirement': 'mandatory'},
    },
    'Python 3.13.5' : { # Windows 11
        # matplotlib dependencies
        'matplotlib': {'versions': ['3.10.3'], 'requirement': 'mandatory'},
        'contourpy': {'versions': ['1.3.2'], 'requirement': 'mandatory'},
        'numpy': {'versions': ['2.3.0'], 'requirement': 'mandatory'},
        'cycler': {'versions': ['0.12.1'], 'requirement': 'mandatory'},
        'fonttools': {'versions': ['4.58.4'], 'requirement': 'mandatory'},
        'kiwisolver': {'versions': ['1.4.8'], 'requirement': 'mandatory'},
        'packaging': {'versions': ['25.0'], 'requirement': 'mandatory'},
        'pillow': {'versions': ['11.2.1'], 'requirement': 'mandatory'},
        'pyparsing': {'versions': ['3.2.3'], 'requirement': 'mandatory'},
        'python-dateutil': {'versions': ['2.9.0.post0'], 'requirement': 'mandatory'},
        'six': {'versions': ['1.17.0'], 'requirement': 'mandatory'},

        # pandas dependencies
        'pandas': {'versions': ['2.3.0'], 'requirement': 'mandatory'},
        'pytz': {'versions': ['2025.2'], 'requirement': 'mandatory'},
        'tzdata': {'versions': ['2025.2'], 'requirement': 'mandatory'},

        # sounddevice dependencies
        'sounddevice': {'versions': ['0.5.2'], 'requirement': 'optional'},
        'cffi': {'versions': ['1.17.1'], 'requirement': 'optional'},
        'pycparser': {'versions': ['2.22'], 'requirement': 'optional'},

        # pyephem dependencies
        'pyephem': {'versions': ['9.99'], 'requirement': 'mandatory'},
        'ephem': {'versions': ['4.2'], 'requirement': 'mandatory'},

        # standalone
        'pip': {'versions': ['25.1.1'], 'requirement': 'mandatory'},
        'pyaudio': {'versions': ['0.2.14'], 'requirement': 'optional'},
        'pyalsaaudio': {'versions': ['0.9.0'], 'requirement': 'optional'},

        # builtin
        'itertools': {'versions': ['builtin'], 'requirement': 'mandatory'},
        'msvcrt': {
            'versions': ['builtin'],
            'requirement': 'OS dependent (Windows)'},
        'sys': {'versions': ['builtin'], 'requirement': 'mandatory'},
        'time': {'versions': ['builtin'], 'requirement': 'mandatory'},
    },
}


if __name__ == '__main__':
    python_version = f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    if python_version in tested_versions:
        identified_versions = {}
        modules = tested_versions[python_version]
        for module in modules:
            try:
                if (module in sys.builtin_module_names):
                    identified_versions[module] = 'builtin'
                else:
                    identified_versions[module] = \
                        version(module)

                if identified_versions[module] in \
                        modules[module]['versions']:
                    print(
                        "SUCCESS: {} '{}' found version {}"
                        .format(
                            modules[module]['requirement'],
                            module,
                            identified_versions[module]))
                else:
                    print(
                        "WARNING: {} '{}' found version {}, expected version(s) {}"
                        .format(
                            modules[module]['requirement'],
                            module,
                            identified_versions[module],
                            modules[module]['versions']))
            except Exception as e:
                if 'mandatory' == modules[module]['requirement']:
                    print("ERROR: {} '{}' not found".format(
                        modules[module]['requirement'], module))
                else:
                    print("INFO: {} '{}' not found".format(
                        modules[module]['requirement'], module))
    else:
        print(f"{python_version} is not tested")
