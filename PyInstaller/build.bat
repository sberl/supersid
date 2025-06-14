REM preconditions:
REM pip install --upgrade pyinstaller
REM pip install uncompyle6

rmdir /S /Q ..\Program
python -m PyInstaller --specpath specs --noconfirm ..\supersid\config.py
python -m PyInstaller --specpath specs --noconfirm ..\supersid\ftp_to_stanford.py
python -m PyInstaller --specpath specs --noconfirm ..\supersid\sampler.py
python -m PyInstaller --specpath specs --noconfirm ..\supersid\sidfile.py
python -m PyInstaller --specpath specs --noconfirm ..\supersid\supersid.py
python -m PyInstaller --specpath specs --noconfirm ..\supersid\supersid_plot.py
python -m PyInstaller --specpath specs --noconfirm ..\supersid\supersid_plot_gui.py
python -m PyInstaller --specpath specs --noconfirm ..\supersid\supersid_scanner.py
python copy_dist.py
