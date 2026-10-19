@echo off
REM ============================================================
REM  Baby Monitoring System - PUBLIC WEBSITE launcher
REM
REM  Starts the app and creates a free public HTTPS URL using
REM  Cloudflare Tunnel. Share that URL with anyone on the internet.
REM
REM  IMPORTANT: your laptop must stay ON and this window must stay OPEN.
REM  The webcam runs on YOUR laptop, so the live feed is real.
REM ============================================================
cd /d "%~dp0"

echo.
echo   Baby Monitoring System - starting public website...
echo.

REM --- 1. start the app ---
start "Baby Monitor Server" cmd /k "cd /d ""%~dp0"" && venv311\Scripts\python.exe -m streamlit run app.py --server.headless true --server.port 8501 --browser.gatherUsageStats false"

echo   Waiting for the app to start...
timeout /t 20 /nobreak >nul

REM --- 2. start the tunnel ---
echo   Creating public URL...
echo.
start "Baby Monitor Tunnel" cmd /k ""C:\Program Files (x86)\cloudflared\cloudflared.exe" tunnel --url http://localhost:8501 --no-autoupdate"

echo.
echo   ==========================================================
echo    The public URL appears in the "Baby Monitor Tunnel" window.
echo    Look for a line containing  https://....trycloudflare.com
echo.
echo    Open that URL in your browser to see the app.
echo    Keep both windows open while sharing.
echo   ==========================================================
echo.
pause
