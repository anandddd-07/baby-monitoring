@echo off
REM Launch the Baby Monitoring System Streamlit demo.
cd /d "%~dp0"

if exist "venv311\Scripts\python.exe" (
    "venv311\Scripts\python.exe" -m streamlit run app.py
) else (
    python -m streamlit run app.py
)
pause
