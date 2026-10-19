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
 --collect-all keras ^
 --collect-all optree ^
 --collect-all cv2 ^
 --collect-all sklearn ^
 --hidden-import detect_file ^
 --hidden-import motion ^
 --hidden-import voice ^
 --hidden-import keras ^
 --hidden-import keras.models ^
 --hidden-import keras.layers ^
 --hidden-import keras.saving ^
 --hidden-import optree ^
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

REM Keras 3 needs optree, and its compiled .pyd plus DLLs live in a sibling
REM folder that PyInstaller does not always pick up. Copy them in manually.
if exist "dist\BabyMonitor\_internal" (
    for %%D in (optree optree.libs) do (
        if exist "venv311\Lib\site-packages\%%D" (
            xcopy /E /I /Y /Q "venv311\Lib\site-packages\%%D" "dist\BabyMonitor\_internal\%%D" >nul
        )
    )
)

echo.
echo Build finished. The app is in:  dist\BabyMonitor\BabyMonitor.exe
pause
