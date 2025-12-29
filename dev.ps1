<#
.SYNOPSIS
    HealthCentral Development Server Startup Script
.DESCRIPTION
    Checks for dependencies, creates virtual environment if needed,
    installs packages, and starts both backend and frontend servers.
.EXAMPLE
    .\dev.ps1
#>

$ErrorActionPreference = "Stop"

# Colors for output
function Write-Status { param($msg) Write-Host "[*] $msg" -ForegroundColor Cyan }
function Write-Success { param($msg) Write-Host "[+] $msg" -ForegroundColor Green }
function Write-Warning { param($msg) Write-Host "[!] $msg" -ForegroundColor Yellow }
function Write-Error { param($msg) Write-Host "[-] $msg" -ForegroundColor Red }

$ROOT_DIR = $PSScriptRoot
$BACKEND_DIR = Join-Path $ROOT_DIR "src\backend"
$FRONTEND_DIR = Join-Path $ROOT_DIR "src\frontend"
$VENV_DIR = Join-Path $BACKEND_DIR "venv"

Write-Host ""
Write-Host "========================================" -ForegroundColor Magenta
Write-Host "  HealthCentral Development Server" -ForegroundColor Magenta
Write-Host "========================================" -ForegroundColor Magenta
Write-Host ""

# Check Python
Write-Status "Checking Python installation..."
$pythonCmd = $null
foreach ($cmd in @("python", "python3", "py")) {
    try {
        $version = & $cmd --version 2>&1
        if ($version -match "Python 3\.(\d+)") {
            $minorVersion = [int]$Matches[1]
            if ($minorVersion -ge 10) {
                $pythonCmd = $cmd
                Write-Success "Found $version"
                break
            }
        }
    } catch { }
}

if (-not $pythonCmd) {
    Write-Error "Python 3.10+ is required but not found."
    Write-Host "Please install Python from https://python.org" -ForegroundColor Gray
    exit 1
}

# Check Node.js
Write-Status "Checking Node.js installation..."
try {
    $nodeVersion = & node --version 2>&1
    if ($nodeVersion -match "v(\d+)\.") {
        $majorVersion = [int]$Matches[1]
        if ($majorVersion -ge 18) {
            Write-Success "Found Node.js $nodeVersion"
        } else {
            Write-Warning "Node.js 18+ recommended. Found $nodeVersion"
        }
    }
} catch {
    Write-Error "Node.js is required but not found."
    Write-Host "Please install Node.js from https://nodejs.org" -ForegroundColor Gray
    exit 1
}

# Check npm
Write-Status "Checking npm..."
try {
    $npmVersion = & npm --version 2>&1
    Write-Success "Found npm v$npmVersion"
} catch {
    Write-Error "npm is required but not found."
    exit 1
}

# Setup Python virtual environment
Write-Status "Checking Python virtual environment..."
if (-not (Test-Path $VENV_DIR)) {
    Write-Warning "Virtual environment not found. Creating..."
    Push-Location $BACKEND_DIR
    & $pythonCmd -m venv venv
    Pop-Location
    Write-Success "Virtual environment created"
} else {
    Write-Success "Virtual environment exists"
}

# Activate venv and install Python dependencies
Write-Status "Checking Python dependencies..."
$venvPython = Join-Path $VENV_DIR "Scripts\python.exe"
$venvPip = Join-Path $VENV_DIR "Scripts\pip.exe"

if (-not (Test-Path $venvPython)) {
    Write-Error "Virtual environment Python not found at $venvPython"
    exit 1
}

# Check if key packages are installed
$packagesInstalled = $true
try {
    $installedPackages = & $venvPip list --format=freeze 2>&1
    foreach ($pkg in @("fastapi", "uvicorn", "sqlalchemy")) {
        if ($installedPackages -notmatch $pkg) {
            $packagesInstalled = $false
            break
        }
    }
} catch {
    $packagesInstalled = $false
}

if (-not $packagesInstalled) {
    Write-Warning "Installing Python dependencies..."
    Push-Location $BACKEND_DIR
    & $venvPip install -r requirements.txt
    Pop-Location
    Write-Success "Python dependencies installed"
} else {
    Write-Success "Python dependencies already installed"
}

# Check Node.js dependencies
Write-Status "Checking Node.js dependencies..."
$nodeModulesDir = Join-Path $FRONTEND_DIR "node_modules"

if (-not (Test-Path $nodeModulesDir)) {
    Write-Warning "Node modules not found. Installing..."
    Push-Location $FRONTEND_DIR
    & npm install
    Pop-Location
    Write-Success "Node.js dependencies installed"
} else {
    Write-Success "Node.js dependencies already installed"
}

# Create data directory if needed
$dataDir = Join-Path $ROOT_DIR "data"
if (-not (Test-Path $dataDir)) {
    Write-Status "Creating data directory..."
    New-Item -ItemType Directory -Path $dataDir -Force | Out-Null
    New-Item -ItemType Directory -Path (Join-Path $dataDir "vaults") -Force | Out-Null
    Write-Success "Data directory created"
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Starting Development Servers" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Backend:  http://localhost:8000" -ForegroundColor Cyan
Write-Host "  API Docs: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "  Frontend: http://localhost:3000" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Press Ctrl+C to stop both servers" -ForegroundColor Gray
Write-Host ""

# Start backend in background job
$backendJob = Start-Job -ScriptBlock {
    param($backendDir, $venvPython)
    Set-Location $backendDir
    $env:PYTHONUNBUFFERED = "1"
    & $venvPython -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
} -ArgumentList $BACKEND_DIR, $venvPython

# Give backend a moment to start
Start-Sleep -Seconds 2

# Start frontend in background job
$frontendJob = Start-Job -ScriptBlock {
    param($frontendDir)
    Set-Location $frontendDir
    & npm run dev
} -ArgumentList $FRONTEND_DIR

Write-Success "Both servers starting..."
Write-Host ""

# Function to cleanup jobs on exit
function Stop-DevServers {
    Write-Host ""
    Write-Status "Stopping servers..."
    Stop-Job -Job $backendJob -ErrorAction SilentlyContinue
    Stop-Job -Job $frontendJob -ErrorAction SilentlyContinue
    Remove-Job -Job $backendJob -Force -ErrorAction SilentlyContinue
    Remove-Job -Job $frontendJob -Force -ErrorAction SilentlyContinue
    Write-Success "Servers stopped"
}

# Register cleanup on Ctrl+C
$null = Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action { Stop-DevServers }

try {
    # Stream output from both jobs
    while ($true) {
        # Check if jobs are still running
        $backendState = $backendJob.State
        $frontendState = $frontendJob.State

        # Get and display output
        $backendOutput = Receive-Job -Job $backendJob -ErrorAction SilentlyContinue
        $frontendOutput = Receive-Job -Job $frontendJob -ErrorAction SilentlyContinue

        if ($backendOutput) {
            $backendOutput | ForEach-Object { Write-Host "[Backend] $_" -ForegroundColor Blue }
        }
        if ($frontendOutput) {
            $frontendOutput | ForEach-Object { Write-Host "[Frontend] $_" -ForegroundColor Magenta }
        }

        # Check for failures
        if ($backendState -eq "Failed") {
            Write-Error "Backend server failed!"
            Receive-Job -Job $backendJob
            break
        }
        if ($frontendState -eq "Failed") {
            Write-Error "Frontend server failed!"
            Receive-Job -Job $frontendJob
            break
        }

        Start-Sleep -Milliseconds 500
    }
} finally {
    Stop-DevServers
}
