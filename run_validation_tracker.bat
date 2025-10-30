@echo off
echo Starting Streamlit app in WSL...

setlocal
set "CURRENT_DIR=%~dp0"

REM Convert Windows path to WSL path
for /f %%i in ('wsl wslpath "%CURRENT_DIR%"') do set "WSL_DIR=%%i"

REM Open browser to Streamlit local URL
start "" http://localhost:8501

REM Run Streamlit app inside WSL using venv
wsl bash -c "cd '%WSL_DIR%' && source venv/bin/activate && export DB_PATH='%WSL_DIR%/TrackerSource/project_tracker.db' && streamlit run TrackerSource/TRACKER.py --server.port 8501"

endlocal