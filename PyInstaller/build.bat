REM preconditions:
REM pip install --upgrade pyinstaller

rmdir /S /Q ..\Program
del ..\SuperSID.zip
python -m PyInstaller --icon=..\supersid.ico --specpath specs --noconfirm ..\supersid\config.py
python -m PyInstaller --icon=..\supersid.ico --specpath specs --noconfirm ..\supersid\ftp_to_stanford.py
python -m PyInstaller --icon=..\supersid.ico --specpath specs --noconfirm ..\supersid\sampler.py
python -m PyInstaller --icon=..\supersid.ico --specpath specs --noconfirm ..\supersid\sidfile.py
python -m PyInstaller --icon=..\supersid.ico --specpath specs --noconfirm ..\supersid\supersid.py
python -m PyInstaller --icon=..\supersid.ico --specpath specs --noconfirm ..\supersid\supersid_plot.py
python -m PyInstaller --icon=..\supersid.ico --specpath specs --noconfirm ..\supersid\supersid_plot_gui.py
python -m PyInstaller --icon=..\supersid.ico --specpath specs --noconfirm ..\supersid\supersid_scanner.py
python copy_dist.py
