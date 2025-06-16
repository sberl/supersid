REM @echo off

REM preconditions:
REM pip install --upgrade pyinstaller

REM ========================
REM 1) compile python to exe
REM ========================

if ("%1" == "clean") (
    rmdir /S /Q build
    rmdir /S /Q dist
    rmdir /S /Q spec
)

python -m PyInstaller --icon=..\supersid.ico --specpath specs --noconfirm ..\src\config.py
python -m PyInstaller --icon=..\supersid.ico --specpath specs --noconfirm ..\src\ftp_to_stanford.py
python -m PyInstaller --icon=..\supersid.ico --specpath specs --noconfirm ..\src\sampler.py
python -m PyInstaller --icon=..\supersid.ico --specpath specs --noconfirm ..\src\sidfile.py
python -m PyInstaller --icon=..\supersid.ico --specpath specs --noconfirm ..\src\supersid.py
python -m PyInstaller --icon=..\supersid.ico --specpath specs --noconfirm --copy-metadata=readchar ..\src\supersid.py
python -m PyInstaller --icon=..\supersid.ico --specpath specs --noconfirm ..\src\supersid_plot.py
python -m PyInstaller --icon=..\supersid.ico --specpath specs --noconfirm ..\src\supersid_plot_gui.py
python -m PyInstaller --icon=..\supersid.ico --specpath specs --noconfirm ..\src\supersid_scanner.py
python -m PyInstaller --icon=..\supersid.ico --specpath specs --noconfirm --copy-metadata=readchar ..\src\supersid_scanner.py

REM ========================
REM 2) create distributable
REM ========================

rmdir /S /Q ..\Program
mkdir ..\Program
del ..\SuperSID.zip

python copy_dist.py

:end