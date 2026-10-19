# Baby Monitoring System

A webcam-based baby monitoring demo that detects:

- whether the baby is **awake** or **sleeping**
- whether the baby is **moving** or **still**
- whether the baby is **inside** or **outside** a safe area

The system also shows live status cards, an event log, charts, session summary, and voice/file alerts.

## Main files

- `app.py` - Streamlit web interface
- `detect_file.py` - main detection pipeline
- `motion.py` - body-motion feature extraction
- `train_motion.py` - trains the body-motion classifier
- `train_eye.py` / `training.py` - eye-model training scripts
- `voice.py` - alert speech and custom audio playback
- `main.py` - desktop OpenCV demo
- `run_app.py` - launcher used by the packaged Windows app
- `build_app.bat` - one-click PyInstaller build script
- `run_streamlit_demo.bat` - one-click launcher for the local app

## Requirements

- Python 3.11 recommended
- A working webcam

Install dependencies:

```powershell
python -m venv venv311
venv311\Scripts\activate
pip install -r requirements.txt
```

## Run the Streamlit app

```powershell
venv311\Scripts\python.exe -m streamlit run app.py
```

Then:

1. Turn on **Start camera**.
2. Set the safe area with the sliders.
3. Test still, awake, moving, and outside states.

## Custom audio

Place these files in `audio/`:

- `wakeup.wav`
- `outside.wav`
- `moving.wav`
- `calm.wav`

`.mp3` and `.ogg` files also work if `pygame` is installed.

## Notes

- `venv311/` and Python installer files are intentionally not stored in this repository.
- The body-motion threshold can be adjusted in the app with **Movement sensitivity**.

## Build a standalone Windows app (.exe)

The project can be packaged into a single double-clickable app with PyInstaller.

```powershell
venv311\Scripts\pip install pyinstaller
```

Then either run the helper script:

```text
build_app.bat
```

or build directly:

```powershell
venv311\Scripts\pyinstaller --noconfirm --name BabyMonitor --onedir --console ^
 --collect-all streamlit --collect-all mediapipe --collect-all tensorflow ^
 --collect-all cv2 --collect-all sklearn ^
 --hidden-import detect_file --hidden-import motion --hidden-import voice ^
 --add-data "app.py;." --add-data "detect_file.py;." --add-data "motion.py;." ^
 --add-data "voice.py;." --add-data "model.h5;." --add-data "model30.h5;." ^
 --add-data "motion_model.json;." --add-data "audio;audio" --add-data "image;image" ^
 run_app.py
```

The finished app is at:

```text
dist\BabyMonitor\BabyMonitor.exe
```

`run_app.py` starts Streamlit in the background and opens your default browser, so the
packaged app behaves exactly like the local one, including the live webcam.
Keep the whole `dist\BabyMonitor` folder together when copying it to another PC.

