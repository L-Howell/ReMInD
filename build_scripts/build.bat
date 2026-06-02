@echo off
echo Building ReMInD executable...

echo Installing requirements...
pip install -r requirements_build.txt

echo Building ReMInD...
pyinstaller --onefile --windowed --name "ReMInD" --add-data "../src/metadata_extractors;metadata_extractors" ../src/remind.py

echo Moving executable to dist folder...
move dist\*.exe ..\dist\

echo Build complete!
pause
