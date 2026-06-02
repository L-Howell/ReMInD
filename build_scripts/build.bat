@echo off
echo Building ReMInD executable...
echo.
echo NOTE: run this from an ACTIVATED conda env (e.g. "conda activate remind-py312").
echo Activation puts the env's Library\bin on PATH, which PyInstaller needs to find
echo the Tcl/Tk and other DLLs - otherwise the resulting exe fails to launch.
echo.

echo Installing requirements...
pip install -r requirements_build.txt

echo Building ReMInD...
REM --collect-all is required for ome_types/xsdata: they load submodules (e.g.
REM xsdata_pydantic_basemodel.hooks) dynamically, which PyInstaller misses otherwise.
pyinstaller --onefile --windowed --name "ReMInD" --noconfirm ^
    --add-data "../src/metadata_extractors;metadata_extractors" ^
    --collect-all ome_types ^
    --collect-all xsdata ^
    --collect-all xsdata_pydantic_basemodel ^
    ../src/remind.py

echo Moving executable to dist folder...
move dist\*.exe ..\dist\

echo Build complete!
pause
