REM @echo off

REM preconditions:
REM pip install --upgrade pyinstaller

REM ========================
REM 1) compile python to exe
REM ========================

if /I "%1" == "clean" (
    if exist build rmdir /S /Q build
    if exist dist rmdir /S /Q dist
    if exist spec rmdir /S /Q spec
)

python -m PyInstaller --icon=..\supersid.ico --specpath specs --noconfirm ..\src\supersid_config.py
python -m PyInstaller --icon=..\supersid.ico --specpath specs --noconfirm ..\src\ftp_to_stanford.py
python -m PyInstaller --icon=..\supersid.ico --specpath specs --noconfirm ..\src\supersid_sampler.py
python -m PyInstaller --icon=..\supersid.ico --specpath specs --noconfirm ..\src\supersid_sidfile.py
python -m PyInstaller --icon=..\supersid.ico --specpath specs --noconfirm --copy-metadata=readchar ..\src\supersid.py
python -m PyInstaller --icon=..\supersid.ico --specpath specs --noconfirm ..\src\supersid_plot.py
python -m PyInstaller --icon=..\supersid.ico --specpath specs --noconfirm ..\src\supersid_plot_gui.py
python -m PyInstaller --icon=..\supersid.ico --specpath specs --noconfirm --copy-metadata=readchar ..\src\supersid_scanner.py

REM ========================
REM 2) create distributable
REM ========================

rmdir /S /Q ..\Program
mkdir ..\Program
if exist ..\SuperSID.zip del ..\SuperSID.zip

python copy_dist.py

:end