# E2E Test Runner for Windows
# Sprint 1 - S1-E2E-001
#
# Usage: .\scripts\e2e-runner.ps1 [filter]
# Example: .\scripts\e2e-runner.ps1 auth

param(
    [string]$Filter = ""
)

$ErrorActionPreference = "Stop"

Write-Host "Asclexis E2E Test Runner" -ForegroundColor Cyan
Write-Host "=============================" -ForegroundColor Cyan

# Navigate to frontend directory
$frontendDir = Join-Path $PSScriptRoot "..\src\frontend"
Push-Location $frontendDir

try {
    # Install Playwright browsers if not already installed
    Write-Host "`nChecking Playwright browsers..." -ForegroundColor Yellow
    npx playwright install chromium --with-deps 2>&1 | Out-Null

    # Build the grep argument if filter provided
    $grepArg = ""
    if ($Filter) {
        $grepArg = "--grep `"$Filter`""
        Write-Host "`nRunning tests matching: $Filter" -ForegroundColor Yellow
    } else {
        Write-Host "`nRunning all E2E tests..." -ForegroundColor Yellow
    }

    # Run Playwright tests (chromium project only — excludes real-PDF local suite)
    $command = "npx playwright test --project chromium $grepArg"
    Write-Host "Executing: $command" -ForegroundColor Gray
    Invoke-Expression $command

    $exitCode = $LASTEXITCODE
    if ($exitCode -eq 0) {
        Write-Host "`nAll E2E tests passed!" -ForegroundColor Green
    } else {
        Write-Host "`nSome E2E tests failed. Exit code: $exitCode" -ForegroundColor Red
    }

    exit $exitCode
}
finally {
    Pop-Location
}
