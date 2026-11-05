@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" main.py
) else if exist "HW\.venv\Scripts\python.exe" (
  "HW\.venv\Scripts\python.exe" main.py
) else (
  echo Python environment is not installed. Follow README.md setup instructions.
)
pause
