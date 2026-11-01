@echo off
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Bitte Python 3.11 oder neuer mit Tcl/Tk von python.org installieren.
  pause
  exit /b 1
)
py -3 -m venv .venv
if errorlevel 1 goto fail
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto fail
echo Fertig. Start-Steburn.bat startet das Programm.
pause
exit /b 0
:fail
echo Einrichtung fehlgeschlagen. Bitte Fehlermeldung kopieren.
pause
exit /b 1
