@echo off
echo Building ReMInD executable...
echo.
echo NOTE: with conda, run this from an ACTIVATED env (e.g. "conda activate remind-py312").
echo Activation puts the env's Library\bin on PATH, which PyInstaller needs to find
echo the Tcl/Tk and other DLLs - otherwise the resulting exe fails to launch.
echo.

echo Installing requirements...
pip install -r requirements_build.txt
if errorlevel 1 exit /b 1

echo Building ReMInD...
REM --icon sets the icon of the .exe file; --add-data ships the same file so
REM the program can use it for its window.
pyinstaller --onefile --windowed --name "ReMInD" --noconfirm ^
    --icon "../ReMInD.ico" ^
    --add-data "../ReMInD.ico;." ^
    ../src/remind.py
if errorlevel 1 exit /b 1

echo Moving executable to dist folder...
if not exist ..\dist mkdir ..\dist
move /y dist\ReMInD.exe ..\dist\
if errorlevel 1 exit /b 1

echo Build complete!
REM CI sets this variable; there is nobody to press a key there.
if not defined CI pause
