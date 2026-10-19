@echo off
REM ============================================================
REM  Baby Monitoring System - one-click launcher
REM  Starts the app and opens it in your browser.
REM ============================================================
cd /d "%~dp0"

if exist "venv311\Scripts\python.exe" (
    set "PY=venv311\Scripts\python.exe"
) else (
    set "PY=python"
)

echo.
echo   Starting Baby Monitoring System...
echo   The browser will open in a few seconds.
echo   Keep this window open.
echo.

start "" "%PY%" -m streamlit run app.py --server.headless true --server.port 8501 --browser.gatherUsageStats false

REM Give Streamlit time to boot, then open the browser.
timeout /t 12 /nobreak >nul
start "" "http://localhost:8501"

echo   App running at http://localhost:8501
echo   Press Ctrl+C then Y to stop.
echo.
