# Backend test runner for HealthCentral (Windows PowerShell).
#
# Usage:
#   .\scripts\run-backend-tests.ps1                              # run all tests
#   .\scripts\run-backend-tests.ps1 tests\test_bootstrap_check.py -q
#
# This script:
#   1. Sets PYTHONPATH so imports resolve from src\backend.
#   2. Sets TEST_MODE=1.
#   3. Invokes pytest with any extra arguments.

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
$BackendDir = Join-Path $RepoRoot "src\backend"

$env:PYTHONPATH = $BackendDir
$env:TEST_MODE = "1"

Set-Location $BackendDir

Write-Host "Running backend tests from $BackendDir"
Write-Host "PYTHONPATH=$env:PYTHONPATH"
Write-Host "---"

python -m pytest @args
