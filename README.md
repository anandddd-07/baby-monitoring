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
- `train_eye.py` - trains the eye-state model (scikit-learn Random Forest)
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

## Run it as a PUBLIC website

The webcam is physically attached to your laptop, so the app has to run on your
machine. A **tunnel** forwards your local app to a public https address so anyone
on the internet can watch the live feed.

Double-click:

```text
start_public_website.bat
```

Or run:

```powershell
venv311\Scripts\python.exe public_website.py
```

This starts the app, creates a public URL, prints it, and opens it in your
browser. The app then shows a green **PUBLIC WEBSITE** banner with the address.

The URL is a free random `trycloudflare.com` address and changes on every start.
Your laptop must stay on and the window must stay open while you share.

To also get a desktop shortcut with an icon, run this once:

```powershell
venv311\Scripts\python.exe create_desktop_shortcut.py
```

It creates **Baby Monitor - Public Website** on your desktop.

| File | What it does |
|---|---|
| `start_public_website.bat` | Public URL, opens in browser |
| `public_website.py` | The script behind it |
| `create_desktop_shortcut.py` | Makes the desktop icon |
| `start_baby_monitor.bat` | Packaged `.exe` (localhost only) |
| `run_streamlit_demo.bat` | Fastest local run, no tunnel |

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

## How the models work

Both classifiers are classic machine learning (scikit-learn):

- **Eye state** - `train_eye.py` turns each 30-frame window of EAR values into five
  features (mean, std, min, max, last) and trains a `RandomForestClassifier`,
  saved as `eye_model.joblib`. `detect_file.py` predicts every 10th frame.
- **Body motion** - `train_motion.py` trains a `LogisticRegression` on three
  motion features, saved as `motion_model.json`.
- **Safe area** - rule-based geometry: five body landmarks are tested against
  the user-drawn polygon with Shapely.

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
 --collect-all streamlit --collect-all mediapipe ^
 --collect-all cv2 --collect-all sklearn ^
 --hidden-import detect_file --hidden-import motion --hidden-import voice ^
 --add-data "app.py;." --add-data "detect_file.py;." --add-data "motion.py;." ^
 --add-data "voice.py;." --add-data "eye_model.joblib;." ^
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

Because the models are small scikit-learn files (`eye_model.joblib`, `motion_model.json`)
there is no heavy framework dependency, so the packaged app starts fast and stays small.

