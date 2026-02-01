@echo off
REM E2E Test Runner for Windows (Batch version)
REM Sprint 1 - S1-E2E-001
REM
REM Usage: scripts\e2e-runner.bat [filter]
REM Example: scripts\e2e-runner.bat auth

echo HealthCentral E2E Test Runner
echo =============================

cd /d "%~dp0..\src\frontend"

if "%1"=="" (
    echo Running all E2E tests...
    npx playwright test
) else (
    echo Running tests matching: %1
    npx playwright test --grep "%1"
)

if %ERRORLEVEL% EQU 0 (
    echo.
    echo All E2E tests passed!
) else (
    echo.
    echo Some E2E tests failed. Exit code: %ERRORLEVEL%
)

exit /b %ERRORLEVEL%
