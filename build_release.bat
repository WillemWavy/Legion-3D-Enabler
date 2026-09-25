@echo off
setlocal
cd /d "%~dp0"
REM Builds Legion 3D Enabler (Release) into a standalone .exe.
REM This version bundles nothing from Lenovo - it sources 3D support files
REM live from your Game Engine install every time you enable 3D.
REM Run this on Windows, in the same folder as legion_3d_enabler_release.py

if not exist "%~dp0icon.ico" (
    echo.
    echo icon.ico not found next to this script - put icon.ico here and
    echo run build_release.bat again.
    echo.
    pause
    exit /b 1
)

if not exist "%~dp0icon.png" (
    echo.
    echo icon.png not found next to this script - put icon.png here and
    echo run build_release.bat again.
    echo.
    pause
    exit /b 1
)

py -m pip install pyinstaller --quiet
py -m PyInstaller --onefile --windowed --name "Legion 3D Enabler" --icon "icon.ico" --add-data "icon.ico;." --add-data "icon.png;." legion_3d_enabler_release.py

echo.
echo Done. Your exe is in the "dist" folder:
echo   dist\Legion 3D Enabler.exe
echo.
echo This build has nothing from Lenovo baked in - it reads live from your
echo Game Engine install every time you enable 3D for a game.
pause
