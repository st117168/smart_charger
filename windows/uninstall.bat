@echo off
cd /d "%~dp0.."

echo [INFO] Killing running processes...
taskkill /F /IM python.exe /T >nul 2>&1
taskkill /F /IM pythonw.exe /T >nul 2>&1
timeout /t 2 /nobreak >nul

echo [INFO] Removing task from Scheduler...
".venv_win\Scripts\python.exe" "__main__.py" --no-autostart

echo [INFO] Deleting virtual environment...
if exist ".venv_win" (
    rd /s /q ".venv_win"
)

echo [INFO] Deleting data...
if exist "data" rd /s /q "data"

echo [SUCCESS] Uninstall complete.

pause
