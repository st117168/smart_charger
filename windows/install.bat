@echo off

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%.."
set "PROJECT_DIR=%CD%"

echo [INFO] Project directory: %PROJECT_DIR%

:: Admin check
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [WARN] Admin rights required! Restarting...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

:: We are trying to find at least some python in the system
where python >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] Python not found in PATH! Install Python.
    pause & exit /b
)

:: Create a data folder
if not exist "data" (
    echo [INFO] Creating a data folder...
    mkdir data
)

:: Create config.json if not
if not exist "data\config.json" (
    echo [INFO] Creating a config.json template...
    (
		echo {
		echo     "tuya": {
		echo         "device_id": "YOUR_DEVICE_ID",
		echo         "local_key": "YOUR_LOCAL_KEY",
		echo         "ip_address": "",
		echo         "version": 3.5
		echo     },
		echo     "battery": {
		echo         "min_level": 30,
		echo         "max_level": 80,
		echo         "check_interval": 60
		echo     }
		echo }
	) > data\config.json
    echo [WARNING] Fill data\config.json with the data of your Tuya device!
)

echo [INFO] Creating virtual environment...
if not exist ".venv_win" (
    python -m venv .venv_win
)

echo [INFO] Installing dependencies...
".venv_win\Scripts\python.exe" -m pip install --upgrade pip
".venv_win\Scripts\python.exe" -m pip install tinytuya psutil pywin32 wmi

echo [INFO] Registering Task Scheduler...
set "TASK_NAME=SmartChargerTask"
set "PYTHONW=%PROJECT_DIR%\.venv_win\Scripts\python.exe"
set "MAIN_PY=%PROJECT_DIR%\__main__.py"

:: Create a task (run from SYSTEM when PC starts)
schtasks /create /tn "%TASK_NAME%" /tr "'%PYTHONW%' '%MAIN_PY%'" /sc onstart /ru "SYSTEM" /rl highest /f

:: Allow battery operation
powershell -Command "Set-ScheduledTask -TaskName '%TASK_NAME%' -Settings (New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries)"

echo [SUCCESS] Installation complete!
pause
