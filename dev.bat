@echo off
REM HealthCentral Development Server Launcher
REM This batch file calls the PowerShell script

echo.
echo Starting HealthCentral Development Environment...
echo.

powershell -ExecutionPolicy Bypass -File "%~dp0dev.ps1"

if %ERRORLEVEL% neq 0 (
    echo.
    echo Failed to start development servers.
    echo If you see an execution policy error, run:
    echo   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
    echo.
    pause
)
