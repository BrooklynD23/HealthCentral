@echo off
setlocal
title Asclexis - Starting...
color 0B

echo.
echo  =============================================
echo   Asclexis - One-Click Launcher
echo  =============================================
echo.
echo  Setting things up for you. Please wait...
echo  If ports 8000 or 3000 are busy, the launcher will pick the next free port.
echo.

REM Run the PowerShell script with bypass policy so double-click always works.
REM -NoProfile skips user profile scripts that might interfere.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0dev.ps1"
set "PS_EXIT=%ERRORLEVEL%"

REM If PowerShell exited with an error, keep the window open so the user can read it.
if %PS_EXIT% neq 0 (
    echo.
    echo  =============================================
    echo   Something went wrong. See the messages above.
    echo  =============================================
    echo.
    echo  Common fixes:
    echo    1. Make sure Python 3.11+ is installed:  https://python.org
    echo    2. Make sure Node.js 22+ is installed:   https://nodejs.org
    echo    3. Restart your computer after installing Python/Node.
    echo    4. Check logs\dev-frontend.log if the frontend exits during startup.
    echo.
    pause
)

exit /b %PS_EXIT%
