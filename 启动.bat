@echo off
chcp 65001 >nul
cd /d "%~dp0"

if "%1"=="--diagnose" goto diag
if "%1"=="--diag" goto diag

echo ============================================
echo   Stickman Drawer - Launcher
echo ============================================
echo.

where pythonw.exe >nul 2>&1
if errorlevel 1 (
    echo [ERROR] pythonw.exe not found in PATH
    echo.
    echo Please install Python 3.8+ and check "Add to PATH":
    echo   https://www.python.org/downloads/
    echo.
    echo Or run with --diagnose option for full environment check
    echo.
    pause
    exit /b 1
)

if exist startup_failed.flag del startup_failed.flag

echo [INFO] Launching...
echo [%date% %time%] Launch ---  >> startup.log

start /B "" pythonw.exe drawstickman.py > startup.log 2>&1

timeout /t 2 /nobreak >nul
tasklist /FI "IMAGENAME eq pythonw.exe" 2>nul | find /I "pythonw.exe" >nul
if errorlevel 1 (
    echo.
    echo [FAILED] Program did not stay running
    echo.
    if exist startup_failed.flag (
        echo ===== Failure Info =====
        type startup_failed.flag
        echo.
    )
    echo ===== startup.log =====
        type startup.log
    echo ========================
    echo.
    echo Try with --diagnose option for full environment check
    pause
) else (
    echo [OK] Program is running
)
exit /b 0

:diag
echo Running environment diagnosis...
python.exe drawstickman.py --diagnose
echo.
echo Diagnosis saved to: diagnose.log
pause
exit /b 0
