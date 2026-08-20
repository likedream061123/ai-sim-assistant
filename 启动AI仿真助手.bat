@echo off
setlocal
title AI Simulation Assistant
cd /d "%~dp0"

set "SILENT=0"
if /i "%~1"=="/silent" set SILENT=1

rem Already running? Open browser and exit.
netstat -ano 2>nul | findstr ":8501 " >nul && (
  if "%SILENT%"=="0" (
    echo [already running] Service is up on http://localhost:8501
    start http://localhost:8501
  )
  exit /b 0
)

if "%SILENT%"=="0" (
  echo Starting AI Simulation Assistant...
  echo Close this window to stop the service.
  echo Browser will open http://localhost:8501 automatically.
  python -m streamlit run app.py --server.port 8501 --server.headless false
  pause
) else (
  start "AI Simulation Assistant" /min python -m streamlit run app.py --server.port 8501 --server.headless true
)
exit /b 0
