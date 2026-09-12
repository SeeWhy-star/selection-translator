@echo off
setlocal
set "PYTHONW=%~dp0.venv\Scripts\pythonw.exe"
if not exist "%PYTHONW%" (
  echo Python environment is missing. Run setup first.
  pause
  exit /b 1
)
start "Selection Translator" "%PYTHONW%" "%~dp0main.py"
