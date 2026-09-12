@echo off
setlocal
set "PYTHON=%~dp0.venv\Scripts\python.exe"
if not exist "%PYTHON%" (
  echo Python environment is missing. Run setup first.
  pause
  exit /b 1
)
pushd "%~dp0"
"%PYTHON%" -m PyInstaller --noconfirm --clean --onefile --windowed --name "SelectionTranslator" --collect-all pystray "%~dp0main.py"
popd
