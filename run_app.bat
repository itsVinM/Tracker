@echo off
echo Starting Tracker App in WSL...

REM Get current directory
setlocal
set "CURRENT_DIR=%~dp0"

REM Convert Windows path to WSL path
for /f %%i in ('wsl wslpath "%CURRENT_DIR%"') do set "WSL_DIR=%%i"

REM Run Python app inside WSL using venv
wsl bash -c "cd '%WSL_DIR%' && source venv/bin/activate && streamlit run TrackerSource/TRACKER.py --server.port 8501"

endlocal