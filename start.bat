@echo off
setlocal
cd /d "%~dp0"

rem ---- find python: project venv > winget user install > PATH ----
set "PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not exist "%PY%" (
  for /f "delims=" %%p in ('where python 2^>nul') do set "PY=%%p"
)
if not exist "%PY%" (
  echo [ERROR] Python 3.10+ not found. Please install Python first.
  pause
  exit /b 1
)

if not exist "venv\Scripts\python.exe" (
  echo [Setup] Creating venv with %PY% ...
  "%PY%" -m venv venv
  if errorlevel 1 ( echo [ERROR] venv create failed. & pause & exit /b 1 )
)

echo [Setup] Checking dependencies ...
"venv\Scripts\python.exe" -m pip install -q -r requirements.txt
if errorlevel 1 ( echo [ERROR] pip install failed, check network. & pause & exit /b 1 )

echo [OK] Starting server at http://127.0.0.1:8322  (close this window to stop)
start "" http://127.0.0.1:8322
"venv\Scripts\python.exe" -m uvicorn src.app:app --host 127.0.0.1 --port 8322
pause
