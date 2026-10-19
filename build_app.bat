@echo off
REM Build the standalone Windows application with PyInstaller.
REM Output: dist\BabyMonitor\BabyMonitor.exe
cd /d "%~dp0"

if not exist "venv311\Scripts\python.exe" (
    echo venv311 was not found. Create it first:
    echo     python -m venv venv311
    echo     venv311\Scripts\pip install -r requirements.txt pyinstaller
    pause
    exit /b 1
)

"venv311\Scripts\python.exe" -m pip install pyinstaller

"venv311\Scripts\pyinstaller" --noconfirm --clean --name BabyMonitor --onedir --console ^
 --collect-all streamlit ^
 --collect-all mediapipe ^
 --collect-all tensorflow ^
 --collect-all cv2 ^
 --collect-all sklearn ^
 --hidden-import detect_file ^
 --hidden-import motion ^
 --hidden-import voice ^
 --add-data "app.py;." ^
 --add-data "detect_file.py;." ^
 --add-data "motion.py;." ^
 --add-data "voice.py;." ^
 --add-data "model.h5;." ^
 --add-data "model30.h5;." ^
 --add-data "motion_model.json;." ^
 --add-data "audio;audio" ^
 --add-data "image;image" ^
 run_app.py

echo.
echo Build finished. The app is in:  dist\BabyMonitor\BabyMonitor.exe
pause
