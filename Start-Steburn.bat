@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo Bitte zuerst Einrichten-Steburn.bat ausfuehren.
  pause
  exit /b 1
)
.venv\Scripts\python.exe main.py
if errorlevel 1 pause
