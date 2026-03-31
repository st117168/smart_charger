@echo off

:: Проверка прав администратора
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Requesting administrator privileges...
    echo.
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

cd /d "%~dp0.."
echo ========================================
echo   Smart Charger Status
echo ========================================
echo.
echo Checking scheduled task...
schtasks /query /tn "SmartChargerTask" 2>nul
if %errorLevel% equ 0 (
    echo [OK] Autostart task exists
) else (
    echo [NO] Autostart task not found
)
echo.
echo Checking Python processes...
tasklist | find "python.exe" >nul
if %errorLevel% equ 0 (
    tasklist | find "python.exe"
) else (
    echo No Python processes running
)
echo.
echo ========================================
pause