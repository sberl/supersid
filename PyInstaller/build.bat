REM preconditions:
REM pip install --upgrade pyinstaller

REM rmdir /S /Q build
REM rmdir /S /Q dist
REM rmdir /S /Q spec
rmdir /S /Q ..\Program
mkdir ..\Program
del ..\SuperSID.zip

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

python copy_dist.py
