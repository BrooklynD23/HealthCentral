<#
.SYNOPSIS
    HealthCentral Development Server Startup Script
.DESCRIPTION
    One-click launcher that checks for dependencies, installs anything missing,
    handles common Windows pitfalls (SQLCipher, corrupted node_modules, port
    conflicts), starts both backend and frontend servers, and opens the browser.
.EXAMPLE
    .\dev.ps1
.NOTES
    Designed so non-technical users can double-click dev.bat and everything works.
#>

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
$ErrorActionPreference = "Continue"   # Don't abort on first non-critical error

$ROOT_DIR     = $PSScriptRoot
$BACKEND_DIR  = Join-Path $ROOT_DIR "src\backend"
$FRONTEND_DIR = Join-Path $ROOT_DIR "src\frontend"
$VENV_DIR     = Join-Path $BACKEND_DIR "venv"
$ENV_FILE     = Join-Path $BACKEND_DIR ".env"
$ENV_EXAMPLE  = Join-Path $ROOT_DIR "config\.env.example"

$BACKEND_PORT  = 8000
$FRONTEND_PORT = 3000

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
function Write-Status  { param($msg) Write-Host "  [*] $msg" -ForegroundColor Cyan }
function Write-Ok      { param($msg) Write-Host "  [+] $msg" -ForegroundColor Green }
function Write-Warn    { param($msg) Write-Host "  [!] $msg" -ForegroundColor Yellow }
function Write-Err     { param($msg) Write-Host "  [-] $msg" -ForegroundColor Red }

function Test-PortInUse {
    param([int]$Port)
    $listener = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue |
                Where-Object { $_.State -eq 'Listen' }
    return $null -ne $listener
}

function Stop-ProcessOnPort {
    param([int]$Port)
    $connections = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue |
                   Where-Object { $_.State -eq 'Listen' }
    foreach ($conn in $connections) {
        try {
            Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
        } catch { }
    }
}

# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------
$host.UI.RawUI.WindowTitle = "HealthCentral"
Write-Host ""
Write-Host "  =============================================" -ForegroundColor Magenta
Write-Host "    HealthCentral  -  Development Server" -ForegroundColor Magenta
Write-Host "  =============================================" -ForegroundColor Magenta
Write-Host ""

# ===================================================================
#  STEP 1  -  Check prerequisites (Python, Node, npm)
# ===================================================================
Write-Host "  --- Checking prerequisites ---" -ForegroundColor DarkGray

# -- Python --
Write-Status "Looking for Python 3.11+ ..."
$pythonCmd = $null
foreach ($cmd in @("python", "python3", "py")) {
    try {
        $version = & $cmd --version 2>&1
        if ($version -match "Python 3\.(\d+)") {
            if ([int]$Matches[1] -ge 11) {
                $pythonCmd = $cmd
                Write-Ok "Found $version"
                break
            }
        }
    } catch { }
}
if (-not $pythonCmd) {
    Write-Err "Python 3.11+ is required but not found."
    Write-Host ""
    Write-Host "    Download it from:  https://python.org/downloads" -ForegroundColor White
    Write-Host "    (Make sure to check 'Add Python to PATH' during install)" -ForegroundColor Gray
    Write-Host ""
    Read-Host "  Press Enter to exit"
    exit 1
}

# -- Node.js --
Write-Status "Looking for Node.js 18+ ..."
$nodeOk = $false
try {
    $nodeVersion = & node --version 2>&1
    if ($nodeVersion -match "v(\d+)\.") {
        if ([int]$Matches[1] -ge 18) {
            Write-Ok "Found Node.js $nodeVersion"
            $nodeOk = $true
        } else {
            Write-Warn "Found Node.js $nodeVersion - version 18+ recommended."
            $nodeOk = $true   # allow older versions to try
        }
    }
} catch { }
if (-not $nodeOk) {
    Write-Err "Node.js is required but not found."
    Write-Host ""
    Write-Host "    Download it from:  https://nodejs.org" -ForegroundColor White
    Write-Host ""
    Read-Host "  Press Enter to exit"
    exit 1
}

# -- npm --
Write-Status "Looking for npm ..."
try {
    $npmVersion = & npm --version 2>&1
    Write-Ok "Found npm v$npmVersion"
} catch {
    Write-Err "npm is required but not found (it ships with Node.js)."
    Read-Host "  Press Enter to exit"
    exit 1
}

Write-Host ""

# ===================================================================
#  STEP 2  -  Python virtual environment
# ===================================================================
Write-Host "  --- Setting up Python backend ---" -ForegroundColor DarkGray

Write-Status "Checking virtual environment ..."
if (-not (Test-Path $VENV_DIR)) {
    Write-Warn "Creating virtual environment (first-time setup) ..."
    Push-Location $BACKEND_DIR
    & $pythonCmd -m venv venv 2>&1 | Out-Null
    Pop-Location
    if (-not (Test-Path (Join-Path $VENV_DIR "Scripts\python.exe"))) {
        Write-Err "Failed to create virtual environment."
        Read-Host "  Press Enter to exit"
        exit 1
    }
    Write-Ok "Virtual environment created"
} else {
    Write-Ok "Virtual environment exists"
}

$venvPython = Join-Path $VENV_DIR "Scripts\python.exe"
$venvPip    = Join-Path $VENV_DIR "Scripts\pip.exe"

# ===================================================================
#  STEP 3  -  Install Python dependencies (with SQLCipher fallback)
# ===================================================================
Write-Status "Installing Python dependencies ..."

# Upgrade pip quietly first
& $venvPython -m pip install --upgrade pip --quiet 2>&1 | Out-Null

# Try full install; if it fails (usually because of sqlcipher3-binary on Windows),
# install everything EXCEPT sqlcipher3-binary and set the env var to skip encryption.
$sqlcipherAvailable = $true
$requirementsFile = Join-Path $BACKEND_DIR "requirements.txt"

Push-Location $BACKEND_DIR
$pipOutput = & $venvPip install -r $requirementsFile 2>&1
$pipExit   = $LASTEXITCODE
Pop-Location

if ($pipExit -ne 0) {
    # Check if sqlcipher was the culprit
    $sqlcipherFailed = ($pipOutput | Out-String) -match "sqlcipher"
    if ($sqlcipherFailed) {
        Write-Warn "SQLCipher is not available on this system (this is normal on Windows)."
        Write-Status "Installing remaining dependencies without SQLCipher ..."
        $sqlcipherAvailable = $false

        # Filter out sqlcipher line and install the rest
        $filteredReqs = Get-Content $requirementsFile |
            Where-Object { $_ -notmatch "sqlcipher" }
        $tempReqs = Join-Path $env:TEMP "hc-requirements-filtered.txt"
        $filteredReqs | Set-Content $tempReqs

        Push-Location $BACKEND_DIR
        & $venvPip install -r $tempReqs --quiet 2>&1 | Out-Null
        Pop-Location

        Remove-Item $tempReqs -Force -ErrorAction SilentlyContinue
        Write-Ok "Python dependencies installed (without SQLCipher)"
    } else {
        Write-Err "Failed to install Python dependencies. Output:"
        $pipOutput | ForEach-Object { Write-Host "    $_" -ForegroundColor DarkRed }
        Read-Host "  Press Enter to exit"
        exit 1
    }
} else {
    Write-Ok "Python dependencies installed"
}

# ===================================================================
#  STEP 4  -  Ensure .env exists with safe defaults
# ===================================================================
Write-Status "Checking .env configuration ..."

if (-not (Test-Path $ENV_FILE)) {
    if (Test-Path $ENV_EXAMPLE) {
        Copy-Item $ENV_EXAMPLE $ENV_FILE
        Write-Ok "Created .env from template"
    } else {
        # Create a minimal .env
        $defaultEnv = @(
            "APP_MODE=local",
            "APP_ENV=development",
            "DEBUG=true",
            "HOST=127.0.0.1",
            "PORT=8000",
            "DATABASE_TYPE=sqlite",
            "DATABASE_ENCRYPTION_ENABLED=true",
            "DATABASE_ENCRYPTION_REQUIRED=false"
        )
        $defaultEnv -join "`r`n" | Set-Content $ENV_FILE
        Write-Ok "Created default .env"
    }
}

# If SQLCipher is not available, make sure encryption is not required
if (-not $sqlcipherAvailable) {
    $envContent = Get-Content $ENV_FILE -Raw
    if ($envContent -match "DATABASE_ENCRYPTION_REQUIRED\s*=\s*true") {
        $envContent = $envContent -replace "DATABASE_ENCRYPTION_REQUIRED\s*=\s*true", "DATABASE_ENCRYPTION_REQUIRED=false"
        Set-Content $ENV_FILE $envContent -NoNewline
        Write-Warn "Set DATABASE_ENCRYPTION_REQUIRED=false (SQLCipher not installed)"
    }
}

Write-Ok ".env is ready"
Write-Host ""

# ===================================================================
#  STEP 5  -  Install Node.js / frontend dependencies
# ===================================================================
Write-Host "  --- Setting up frontend ---" -ForegroundColor DarkGray

$viteBin = Join-Path $FRONTEND_DIR "node_modules\.bin\vite.cmd"
$nodeModulesDir = Join-Path $FRONTEND_DIR "node_modules"

# Install if node_modules missing OR vite binary missing (corrupted install)
if (-not (Test-Path $nodeModulesDir) -or -not (Test-Path $viteBin)) {
    if (Test-Path $nodeModulesDir) {
        Write-Warn "node_modules exists but looks incomplete. Reinstalling ..."
        Remove-Item $nodeModulesDir -Recurse -Force -ErrorAction SilentlyContinue
    } else {
        Write-Status "Installing frontend dependencies (first-time setup) ..."
    }
    Push-Location $FRONTEND_DIR
    & npm install 2>&1 | Out-Null
    Pop-Location

    if (-not (Test-Path $viteBin)) {
        Write-Err "npm install succeeded but Vite was not found."
        Write-Err "Try deleting src\frontend\node_modules and running again."
        Read-Host "  Press Enter to exit"
        exit 1
    }
    Write-Ok "Frontend dependencies installed"
} else {
    Write-Ok "Frontend dependencies already installed"
}

Write-Host ""

# ===================================================================
#  STEP 6  -  Create data directories
# ===================================================================
$dataDir = Join-Path $ROOT_DIR "data"
if (-not (Test-Path $dataDir)) {
    New-Item -ItemType Directory -Path $dataDir -Force | Out-Null
    New-Item -ItemType Directory -Path (Join-Path $dataDir "vaults") -Force | Out-Null
}

# ===================================================================
#  STEP 7  -  Check for port conflicts
# ===================================================================
Write-Host "  --- Checking ports ---" -ForegroundColor DarkGray

if (Test-PortInUse $BACKEND_PORT) {
    Write-Warn "Port $BACKEND_PORT is already in use. Trying to free it ..."
    Stop-ProcessOnPort $BACKEND_PORT
    Start-Sleep -Seconds 1
    if (Test-PortInUse $BACKEND_PORT) {
        Write-Err "Could not free port $BACKEND_PORT. Close the application using it and try again."
        Read-Host "  Press Enter to exit"
        exit 1
    }
    Write-Ok "Port $BACKEND_PORT freed"
} else {
    Write-Ok "Port $BACKEND_PORT is available (backend)"
}

if (Test-PortInUse $FRONTEND_PORT) {
    Write-Warn "Port $FRONTEND_PORT is already in use. Trying to free it ..."
    Stop-ProcessOnPort $FRONTEND_PORT
    Start-Sleep -Seconds 1
    if (Test-PortInUse $FRONTEND_PORT) {
        Write-Err "Could not free port $FRONTEND_PORT. Close the application using it and try again."
        Read-Host "  Press Enter to exit"
        exit 1
    }
    Write-Ok "Port $FRONTEND_PORT freed"
} else {
    Write-Ok "Port $FRONTEND_PORT is available (frontend)"
}

Write-Host ""

# ===================================================================
#  STEP 8  -  Launch servers
# ===================================================================
Write-Host "  =============================================" -ForegroundColor Green
Write-Host "    Starting HealthCentral ..." -ForegroundColor Green
Write-Host "  =============================================" -ForegroundColor Green
Write-Host ""
Write-Host "    Backend API:  http://localhost:$BACKEND_PORT" -ForegroundColor Cyan
Write-Host "    Frontend:     http://localhost:$FRONTEND_PORT" -ForegroundColor Cyan
Write-Host "    API Docs:     http://localhost:$BACKEND_PORT/docs" -ForegroundColor Cyan
Write-Host ""

# We need to pass the current PATH to background jobs so they can find npm/node.
$currentPath = $env:PATH
$npmPath     = (Get-Command npm -ErrorAction SilentlyContinue).Source | Split-Path

# -- Backend (background process) --
$backendProc = Start-Process -FilePath $venvPython `
    -ArgumentList "-m", "uvicorn", "main:app", "--reload", "--host", "127.0.0.1", "--port", "$BACKEND_PORT" `
    -WorkingDirectory $BACKEND_DIR `
    -WindowStyle Hidden `
    -PassThru

# Give backend a head start
Start-Sleep -Seconds 2

# -- Frontend (background process) --
# Use the vite.cmd binary directly so we don't need cmd.exe with && chaining
$frontendVite = Join-Path $FRONTEND_DIR "node_modules\.bin\vite.cmd"
$frontendProc = Start-Process -FilePath $frontendVite `
    -ArgumentList "--port", "$FRONTEND_PORT" `
    -WorkingDirectory $FRONTEND_DIR `
    -WindowStyle Hidden `
    -PassThru

$bPid = $backendProc.Id
$fPid = $frontendProc.Id
Write-Ok "Backend  started  [PID $bPid]"
Write-Ok "Frontend started  [PID $fPid]"
Write-Host ""

# ===================================================================
#  STEP 9  -  Wait for frontend to be ready, then open browser
# ===================================================================
Write-Status "Waiting for servers to be ready ..."

$maxWait = 30       # seconds
$elapsed = 0
$opened  = $false

while ($elapsed -lt $maxWait) {
    Start-Sleep -Seconds 1
    $elapsed++

    try {
        $response = Invoke-WebRequest -Uri "http://localhost:$FRONTEND_PORT" `
                        -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            Write-Ok "Servers are ready!"
            Write-Host ""
            Start-Process "http://localhost:$FRONTEND_PORT"
            $opened = $true
            break
        }
    } catch { }
}

if (-not $opened) {
    Write-Warn "Servers are still starting. Opening browser anyway ..."
    Start-Process "http://localhost:$FRONTEND_PORT"
}

# ===================================================================
#  STEP 10  -  Keep alive & monitor, clean up on exit
# ===================================================================
Write-Host ""
Write-Host "  =============================================" -ForegroundColor Green
Write-Host "    HealthCentral is running!" -ForegroundColor Green
Write-Host "  =============================================" -ForegroundColor Green
Write-Host ""
Write-Host "    Press Ctrl+C or close this window to stop." -ForegroundColor Gray
Write-Host ""

function Stop-Servers {
    Write-Host ""
    Write-Status "Shutting down ..."
    try {
        if (-not $backendProc.HasExited) {
            Stop-Process -Id $backendProc.Id -Force -ErrorAction SilentlyContinue
        }
    } catch { }
    try {
        if (-not $frontendProc.HasExited) {
            Stop-Process -Id $frontendProc.Id -Force -ErrorAction SilentlyContinue
        }
    } catch { }
    Write-Ok "Servers stopped. Goodbye!"
}

try {
    while ($true) {
        Start-Sleep -Seconds 2

        $backendDead  = $backendProc.HasExited
        $frontendDead = $frontendProc.HasExited

        if ($backendDead -and $frontendDead) {
            Write-Warn "Both servers have stopped."
            break
        }
        if ($backendDead) {
            $ec = $backendProc.ExitCode
            Write-Warn "Backend stopped unexpectedly [exit code $ec]. Restarting ..."
            $backendProc = Start-Process -FilePath $venvPython `
                -ArgumentList "-m", "uvicorn", "main:app", "--reload", "--host", "127.0.0.1", "--port", "$BACKEND_PORT" `
                -WorkingDirectory $BACKEND_DIR `
                -WindowStyle Hidden `
                -PassThru
            $bPid = $backendProc.Id
            Write-Ok "Backend restarted [PID $bPid]"
        }
        if ($frontendDead) {
            $ec = $frontendProc.ExitCode
            Write-Warn "Frontend stopped unexpectedly [exit code $ec]. Restarting ..."
            $frontendProc = Start-Process -FilePath $frontendVite `
                -ArgumentList "--port", "$FRONTEND_PORT" `
                -WorkingDirectory $FRONTEND_DIR `
                -WindowStyle Hidden `
                -PassThru
            $fPid = $frontendProc.Id
            Write-Ok "Frontend restarted [PID $fPid]"
        }
    }
} finally {
    Stop-Servers
}
