# Running in VS Code

## Open the project

1. Open VS Code
2. **File → Open Folder** and pick this project folder
3. If asked to trust the folder, choose **Yes, I trust the authors**

## Pick the Python interpreter

Press `Ctrl+Shift+P` → type **Python: Select Interpreter** → choose:

```text
.\venv311\Scripts\python.exe
```

VS Code remembers this because `.vscode/settings.json` already points at it.

## Run it

Press `Ctrl+Shift+P` → type **Tasks: Run Task** → pick one:

| Task | What it does |
|---|---|
| **Run Baby Monitor (Streamlit)** | The web app at `http://localhost:8501` |
| **Run Baby Monitor (public website)** | Web app plus a public `trycloudflare.com` URL |
| **Run Baby Monitor (desktop OpenCV)** | A separate desktop window, no browser |

Or use **Terminal → Run Task** and pick the same list.

The Streamlit task also **starts automatically when you open the folder**.

## Debug it

Press `F5` (or **Run → Start Debugging**) and choose:

- **Baby Monitor (Streamlit app)**
- **Baby Monitor (public website)**
- **Baby Monitor (desktop OpenCV)**

Breakpoints work normally.

## Terminal instead

Open **Terminal → New Terminal** (it should activate `venv311` automatically) and run:

```powershell
.\venv311\Scripts\python.exe -m streamlit run app.py
```

Then open `http://localhost:8501`.

## If something looks wrong

- **Port already in use** — a copy is already running. Stop it in the terminal
  with `Ctrl+C`, or use a different port:
  ```powershell
  .\venv311\Scripts\python.exe -m streamlit run app.py --server.port 8502
  ```
- **Camera not opening** — close other apps using the camera (Teams, Zoom, Chrome
  tabs with camera access).
- **Nothing happens on click** — the app needs the `venv311` interpreter, not the
  system Python. Check the bottom-right corner of VS Code shows `Python 3.11.9`.
