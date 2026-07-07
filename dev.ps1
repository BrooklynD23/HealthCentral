<#
.SYNOPSIS
    HealthCentral Development Server Startup Script
.DESCRIPTION
    One-click launcher that checks for dependencies, installs anything missing,
    handles common Windows pitfalls (SQLCipher, corrupted node_modules, port
    conflicts by resolving the next free port when needed, installs OCR tooling
    on Windows (Tesseract + Poppler via winget when available), syncs
    OCR_ENABLED in src/backend/.env, starts both servers, and opens the browser.
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
    $listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    return $null -ne $listener
}

function Get-ListenerPidsForPort {
    param([int]$Port)
    $ids = @{}
    foreach ($c in @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)) {
        $id = [int]$c.OwningProcess
        if ($id -gt 0) { $ids[$id] = $true }
    }
    if ($ids.Count -gt 0) {
        return @([int[]]($ids.Keys))
    }
    # Fallback when cmdlet omits owners or policy blocks it (English LISTENING lines).
    if ($env:OS -eq 'Windows_NT') {
        foreach ($line in @(netstat -ano 2>$null)) {
            if ($line -notmatch 'LISTENING') { continue }
            if ($line -notmatch "\:$($Port)\s+") { continue }
            if ($line -match 'LISTENING\s+(\d+)\s*$') {
                $id = [int]$Matches[1]
                if ($id -gt 0) { $ids[$id] = $true }
            }
        }
    }
    return @([int[]]($ids.Keys))
}

# Uvicorn --reload: child holds the socket; taskkill /T on the child does not kill the reloader parent,
# which respawns a new listener. Walk ancestors and return the topmost python in the chain (reloader).
function Get-ProcessPortKillTarget {
    param([int]$ProcessId)
    $protected = @{ 0 = $true; 4 = $true }
    if ($protected.ContainsKey($ProcessId)) { return $ProcessId }
    $proc = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
    if (-not $proc) { return $ProcessId }
    $name = $proc.ProcessName
    if ($name -notmatch '^(python|pythonw)(\d+)?$') {
        return $ProcessId
    }
    $topPython = $ProcessId
    $current = $ProcessId
    $seen = @{}
    for ($depth = 0; $depth -lt 32; $depth++) {
        if ($seen.ContainsKey($current)) { break }
        $seen[$current] = $true
        $row = Get-CimInstance -ClassName Win32_Process -Filter "ProcessId=$current" -ErrorAction SilentlyContinue
        if (-not $row) { break }
        $parent = [int]$row.ParentProcessId
        if ($parent -le 0 -or $protected.ContainsKey($parent) -or $parent -eq $current) { break }
        $pProc = Get-Process -Id $parent -ErrorAction SilentlyContinue
        if (-not $pProc) { break }
        $pName = $pProc.ProcessName
        if ($pName -match '^(python|pythonw)(\d+)?$') {
            $topPython = $parent
            $current = $parent
        } else {
            break
        }
    }
    return $topPython
}

function Invoke-ElevatedTaskKill {
    param([int[]]$ProcessIds)
    if ($ProcessIds.Count -eq 0) { return $false }
    $ids = ($ProcessIds | ForEach-Object { "/PID $_" }) -join " "
    # Single UAC prompt; kills process trees for each PID.
    $inner = "taskkill /F /T $ids 2>`$null; exit `$LASTEXITCODE"
    try {
        $p = Start-Process -FilePath "powershell.exe" -Verb RunAs -ArgumentList @(
            "-NoProfile", "-ExecutionPolicy", "Bypass", "-WindowStyle", "Hidden", "-Command", $inner
        ) -PassThru -Wait
        return ($p.ExitCode -eq 0)
    } catch {
        return $false
    }
}

function Write-PortListenerDiagnostics {
    param([int]$Port)
    $pids = Get-ListenerPidsForPort -Port $Port
    if ($pids.Count -eq 0) {
        Write-Warn "Port $Port still looks busy but no listener PID was found (reserved port range, or run as Administrator). Check: netsh interface ipv4 show excludedportrange protocol=tcp"
        return
    }
    foreach ($procId in $pids) {
        $name = (Get-Process -Id $procId -ErrorAction SilentlyContinue).ProcessName
        if ($name) {
            Write-Warn "Still listening on ${Port}: PID $procId ($name). Close it manually, approve the UAC prompt when re-running dev.ps1, or set HC_SKIP_ELEVATED_PORT_KILL=1 and free the port yourself."
        } else {
            Write-Warn "Still listening on ${Port}: PID $procId. Close it manually, approve the UAC prompt when re-running dev.ps1, or set HC_SKIP_ELEVATED_PORT_KILL=1 and free the port yourself."
        }
    }
}

function Stop-ProcessOnPort {
    param([int]$Port)
    # Never kill System idle (0) or the Windows kernel System process (4).
    $protected = @{ 0 = $true; 4 = $true }
    $maxRounds = 10
    for ($round = 0; $round -lt $maxRounds; $round++) {
        if (-not (Test-PortInUse $Port)) { return }
        $pids = Get-ListenerPidsForPort -Port $Port
        if ($pids.Count -eq 0) { return }
        $targets = @{}
        foreach ($procId in $pids) {
            if ($protected.ContainsKey($procId)) { continue }
            $killId = Get-ProcessPortKillTarget -ProcessId $procId
            if (-not $protected.ContainsKey($killId)) { $targets[$killId] = $true }
        }
        $tk = Get-Command taskkill.exe -ErrorAction SilentlyContinue
        foreach ($killId in [int[]]($targets.Keys)) {
            Stop-Process -Id $killId -Force -ErrorAction SilentlyContinue
            if ($tk -and (Get-Process -Id $killId -ErrorAction SilentlyContinue)) {
                & taskkill.exe /F /T /PID $killId 2>$null | Out-Null
            }
        }
        Start-Sleep -Milliseconds 500
    }
    # Same user should not need this; handles protected / odd service cases and stubborn reloaders.
    if ($env:HC_SKIP_ELEVATED_PORT_KILL -eq "1") { return }
    if (-not (Test-PortInUse $Port)) { return }
    $pids = Get-ListenerPidsForPort -Port $Port
    if ($pids.Count -eq 0) { return }
    $targets = @{}
    foreach ($procId in $pids) {
        if ($protected.ContainsKey($procId)) { continue }
        $killId = Get-ProcessPortKillTarget -ProcessId $procId
        if (-not $protected.ContainsKey($killId)) { $targets[$killId] = $true }
    }
    $ids = @([int[]]($targets.Keys))
    if ($ids.Count -eq 0) { return }
    Write-Warn "Port $Port still in use; requesting elevated permission to stop listener(s) (one UAC prompt) ..."
    [void](Invoke-ElevatedTaskKill -ProcessIds $ids)
    Start-Sleep -Milliseconds 800
}

function Find-FreePort {
    param([int]$StartPort, [int]$MaxPort = 65535)
    for ($port = $StartPort; $port -le $MaxPort; $port++) {
        if (-not (Test-PortInUse $port)) { return $port }
    }
    throw "No free port found between $StartPort and $MaxPort"
}

function Refresh-EnvPathFromRegistry {
    $m = [Environment]::GetEnvironmentVariable('Path', 'Machine')
    $u = [Environment]::GetEnvironmentVariable('Path', 'User')
    if ($m -and $u) {
        $env:Path = "$m;$u"
    } elseif ($m) {
        $env:Path = $m
    } elseif ($u) {
        $env:Path = $u
    }
}

function Add-TesseractToPathIfPresent {
    if ($env:OS -ne 'Windows_NT') { return $false }
    $candidates = @(
        (Join-Path $env:ProgramFiles 'Tesseract-OCR'),
        (Join-Path ${env:ProgramFiles(x86)} 'Tesseract-OCR')
    )
    foreach ($dir in $candidates) {
        $exe = Join-Path $dir 'tesseract.exe'
        if (Test-Path -LiteralPath $exe) {
            if ($env:Path -notlike "*$dir*") {
                $env:Path = "$dir;$env:Path"
            }
            return $true
        }
    }
    return $false
}

function Find-PdftoppmAndPrependPath {
    if ($env:OS -ne 'Windows_NT') { return $false }
    if (Get-Command pdftoppm.exe -ErrorAction SilentlyContinue) { return $true }
    $pkgRoot = Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Packages'
    if (-not (Test-Path -LiteralPath $pkgRoot)) { return $false }
    try {
        $hit = Get-ChildItem -Path $pkgRoot -Recurse -Filter 'pdftoppm.exe' -ErrorAction SilentlyContinue |
            Select-Object -First 1
        if ($hit) {
            $bin = Split-Path $hit.FullName -Parent
            if ($env:Path -notlike "*$bin*") {
                $env:Path = "$bin;$env:Path"
            }
            return $true
        }
    } catch { }
    return $false
}

function Set-DotEnvKey {
    param(
        [Parameter(Mandatory)][string]$FilePath,
        [Parameter(Mandatory)][string]$Key,
        [Parameter(Mandatory)][string]$Value
    )
    $pattern = "^\s*$([regex]::Escape($Key))\s*="
    $newLine = "$Key=$Value"
    $lines = if (Test-Path -LiteralPath $FilePath) {
        Get-Content -LiteralPath $FilePath
    } else {
        @()
    }
    $out = New-Object System.Collections.Generic.List[string]
    $found = $false
    foreach ($line in $lines) {
        if ($line -match $pattern) {
            if (-not $found) {
                [void]$out.Add($newLine)
                $found = $true
            }
        } else {
            [void]$out.Add($line)
        }
    }
    if (-not $found) {
        if ($out.Count -gt 0 -and $out[$out.Count - 1] -ne '') { [void]$out.Add('') }
        [void]$out.Add($newLine)
    }
    $out | Set-Content -LiteralPath $FilePath
}

function Start-FrontendDevServer {
    param(
        [Parameter(Mandatory)][string]$NodeExePath,
        [Parameter(Mandatory)][string]$FrontendViteScriptPath,
        [Parameter(Mandatory)][int]$Port,
        [Parameter(Mandatory)][string]$WorkingDirectory,
        [Parameter(Mandatory)][string]$LogPath
    )
    $logDir = Split-Path -Parent $LogPath
    if (-not (Test-Path -LiteralPath $logDir)) {
        New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    }
    # Hidden cmd.exe + shell redirect fails silently; launch node directly (Vite logs to stderr).
    return Start-Process -FilePath $NodeExePath `
        -ArgumentList $FrontendViteScriptPath, "--port", "$Port", "--strictPort" `
        -WorkingDirectory $WorkingDirectory `
        -WindowStyle Hidden `
        -RedirectStandardError $LogPath `
        -PassThru
}

function Write-LogTail {
    param(
        [Parameter(Mandatory)][string]$LogPath,
        [string]$Label = "Log output",
        [int]$Tail = 20
    )
    if (-not (Test-Path -LiteralPath $LogPath)) {
        Write-Warn "$Label not found at $LogPath"
        return
    }
    Write-Warn "$Label (last $Tail lines):"
    Get-Content -LiteralPath $LogPath -Tail $Tail | ForEach-Object { Write-Host "      $_" -ForegroundColor DarkGray }
}

function Test-TesseractOnPath {
    if (Get-Command tesseract -ErrorAction SilentlyContinue) { return $true }
    if (Get-Command tesseract.exe -ErrorAction SilentlyContinue) { return $true }
    return $false
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
function Find-Python311Command {
    foreach ($cmd in @("python", "python3", "py")) {
        try {
            $version = & $cmd --version 2>&1
            if ($version -match "Python 3\.(\d+)") {
                if ([int]$Matches[1] -ge 11) {
                    return [pscustomobject]@{ Cmd = $cmd; Version = "$version" }
                }
            }
        } catch { }
    }
    return $null
}

function Write-PythonManualInstallHelp {
    Write-Host ""
    Write-Host "    Download it from:  https://python.org/downloads" -ForegroundColor White
    Write-Host "    (Make sure to check 'Add Python to PATH' during install)" -ForegroundColor Gray
    Write-Host ""
}

Write-Status "Looking for Python 3.11+ ..."
$pythonCmd = $null
$pythonFound = Find-Python311Command
if ($pythonFound) {
    $pythonCmd = $pythonFound.Cmd
    Write-Ok "Found $($pythonFound.Version)"
}
if (-not $pythonCmd) {
    Write-Err "Python 3.11+ is required but not found."
    $wingetCmd = Get-Command winget -ErrorAction SilentlyContinue
    if (-not $wingetCmd) {
        Write-PythonManualInstallHelp
        Read-Host "  Press Enter to exit"
        exit 1
    }
    $answer = Read-Host "  Python 3.11+ was not found. Install Python 3.11 automatically with winget? [Y/n]"
    if ($answer -and $answer.Trim() -match '^[Nn]') {
        Write-PythonManualInstallHelp
        Read-Host "  Press Enter to exit"
        exit 1
    }
    Write-Status "Installing Python 3.11 via winget (this may take a few minutes) ..."
    & winget install --id Python.Python.3.11 --exact --source winget --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) {
        Write-Err "winget install failed (exit code $LASTEXITCODE)."
        Write-PythonManualInstallHelp
        Read-Host "  Press Enter to exit"
        exit 1
    }
    Refresh-EnvPathFromRegistry
    $pythonFound = Find-Python311Command
    if ($pythonFound) {
        $pythonCmd = $pythonFound.Cmd
        Write-Ok "Found $($pythonFound.Version) (installed via winget)"
    } else {
        Write-Err "winget completed but Python is not visible in this shell."
        Write-Host "    Restart the terminal and run dev.ps1 again, or install manually:" -ForegroundColor White
        Write-PythonManualInstallHelp
        Read-Host "  Press Enter to exit"
        exit 1
    }
}

# -- Node.js --
Write-Status "Looking for Node.js 22+ ..."
$nodeOk = $false
$nodeExe = $null
try {
    $nodeVersion = & node --version 2>&1
    if ($nodeVersion -match "v(\d+)\.") {
        if ([int]$Matches[1] -ge 22) {
            Write-Ok "Found Node.js $nodeVersion"
            $nodeExe = (Get-Command node -ErrorAction Stop).Source
            $nodeOk = $true
        } else {
            Write-Warn "Found Node.js $nodeVersion - version 22+ required (Node.js 24 LTS recommended)."
            $nodeExe = (Get-Command node -ErrorAction Stop).Source
            $nodeOk = $true   # allow older versions to try
        }
    }
} catch { }
# Cursor's bundled node is first on PATH in the IDE but cannot run Vite reliably as a hidden child process.
if ($nodeOk) {
    $programFilesNode = Join-Path ${env:ProgramFiles} "nodejs\node.exe"
    if (Test-Path -LiteralPath $programFilesNode) {
        $nodeExe = $programFilesNode
    } elseif ($nodeExe -match 'cursor[\\/]resources') {
        $altNode = Get-Command node -All -ErrorAction SilentlyContinue |
            Where-Object { $_.Source -notmatch 'cursor[\\/]resources' } |
            Select-Object -First 1
        if ($altNode) { $nodeExe = $altNode.Source }
    }
}
if (-not $nodeOk) {
    Write-Err "Node.js 22+ is required but not found."
    Write-Host ""
    Write-Host "    Download it from:  https://nodejs.org  (Node.js 24 LTS recommended)" -ForegroundColor White
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
#  STEP 3b - OCR system tools (Windows): Tesseract + Poppler
# ===================================================================
# Python wheels (pillow, pytesseract, pdf2image) are installed in STEP 3.
# Set HC_SKIP_OCR_SETUP=1 to skip winget installs and .env OCR_ENABLED sync.
if ($env:HC_SKIP_OCR_SETUP -eq "1") {
    Write-Status "Skipping OCR auto-setup (HC_SKIP_OCR_SETUP=1)."
} elseif ($env:OS -eq "Windows_NT") {
    Write-Host "  --- OCR dependencies (Windows) ---" -ForegroundColor DarkGray
    $winget = Get-Command winget.exe -ErrorAction SilentlyContinue
    Refresh-EnvPathFromRegistry
    [void](Add-TesseractToPathIfPresent)

    $tessOk = Test-TesseractOnPath
    if (-not $tessOk) {
        if ($winget) {
            Write-Status "Installing Tesseract OCR via winget (may require approval) ..."
            $null = & winget install -e --id UB-Mannheim.TesseractOCR --accept-package-agreements --accept-source-agreements 2>&1
            Refresh-EnvPathFromRegistry
            [void](Add-TesseractToPathIfPresent)
        } else {
            Write-Warn "Tesseract not found and winget is unavailable. For scanned PDFs: https://github.com/UB-Mannheim/tesseract/wiki"
        }
    }

    $tessOk = Test-TesseractOnPath
    if ($tessOk) {
        Write-Ok "Tesseract OCR is available"
    } else {
        Write-Warn "Tesseract still not on PATH - restart this window after install, or add Tesseract-OCR to PATH."
    }

    $popOk = [bool](Get-Command pdftoppm.exe -ErrorAction SilentlyContinue)
    if (-not $popOk -and $winget) {
        Write-Status "Installing Poppler via winget (scanned PDF rasterization for OCR) ..."
        $null = & winget install -e --id oschwartz10612.Poppler --accept-package-agreements --accept-source-agreements 2>&1
        Refresh-EnvPathFromRegistry
    }

    $popOk = [bool](Get-Command pdftoppm.exe -ErrorAction SilentlyContinue)
    if (-not $popOk) { $popOk = Find-PdftoppmAndPrependPath }
    if ($popOk) {
        Write-Ok "Poppler (pdftoppm) is available"
    } else {
        Write-Warn "pdftoppm not on PATH - scanned PDF OCR may fail until Poppler is installed (e.g. winget install oschwartz10612.Poppler)."
    }
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

# Match backend gate: OCR_ENABLED is meaningful only when Tesseract is on PATH.
if ($env:HC_SKIP_OCR_SETUP -ne "1") {
    Refresh-EnvPathFromRegistry
    if ($env:OS -eq "Windows_NT") {
        [void](Add-TesseractToPathIfPresent)
    }
    $tesseractResolved = Test-TesseractOnPath
    if (-not $tesseractResolved -and $env:OS -eq "Windows_NT") {
        [void](Add-TesseractToPathIfPresent)
        $tesseractResolved = Test-TesseractOnPath
    }
    Set-DotEnvKey -FilePath $ENV_FILE -Key "OCR_ENABLED" -Value $(if ($tesseractResolved) { "true" } else { "false" })
    if ($tesseractResolved) {
        Write-Ok "Synced .env: OCR_ENABLED=true (Tesseract on PATH)"
    } else {
        Write-Warn "Synced .env: OCR_ENABLED=false (Tesseract not detected - install and re-run dev.ps1)"
    }
}

Write-Ok ".env is ready"
Write-Host ""

# ===================================================================
#  STEP 5  -  Install Node.js / frontend dependencies
# ===================================================================
Write-Host "  --- Setting up frontend ---" -ForegroundColor DarkGray

$viteBin = Join-Path $FRONTEND_DIR "node_modules\.bin\vite.cmd"
$viteScript = Join-Path $FRONTEND_DIR "node_modules\vite\bin\vite.js"
$nodeModulesDir = Join-Path $FRONTEND_DIR "node_modules"

# Install if node_modules missing OR vite binary missing (corrupted install)
if (-not (Test-Path $nodeModulesDir) -or -not (Test-Path $viteBin) -or -not (Test-Path $viteScript)) {
    if (Test-Path $nodeModulesDir) {
        Write-Warn "node_modules exists but looks incomplete. Reinstalling ..."
        Remove-Item $nodeModulesDir -Recurse -Force -ErrorAction SilentlyContinue
    } else {
        Write-Status "Installing frontend dependencies (first-time setup) ..."
    }
    Push-Location $FRONTEND_DIR
    & npm install 2>&1 | Out-Null
    Pop-Location

    if (-not (Test-Path $viteBin) -or -not (Test-Path $viteScript)) {
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
#  STEP 7  -  Resolve ports (best-effort free, then scan for available)
# ===================================================================
Write-Host "  --- Checking ports ---" -ForegroundColor DarkGray

if (Test-PortInUse $BACKEND_PORT) {
    Write-Warn "Port $BACKEND_PORT is in use. Trying to free it ..."
    Stop-ProcessOnPort $BACKEND_PORT
    Start-Sleep -Seconds 1
}
$resolvedBackendPort = Find-FreePort -StartPort $BACKEND_PORT
if ($resolvedBackendPort -ne $BACKEND_PORT) {
    Write-Warn "Port $BACKEND_PORT still in use - using port $resolvedBackendPort for backend"
} else {
    Write-Ok "Port $resolvedBackendPort is available (backend)"
}

if (Test-PortInUse $FRONTEND_PORT) {
    Write-Warn "Port $FRONTEND_PORT is in use. Trying to free it ..."
    Stop-ProcessOnPort $FRONTEND_PORT
    Start-Sleep -Seconds 1
}
$resolvedFrontendPort = Find-FreePort -StartPort $FRONTEND_PORT
if ($resolvedFrontendPort -ne $FRONTEND_PORT) {
    Write-Warn "Port $FRONTEND_PORT still in use - using port $resolvedFrontendPort for frontend"
} else {
    Write-Ok "Port $resolvedFrontendPort is available (frontend)"
}

Write-Host ""

# ===================================================================
#  STEP 7b - Sync frontend .env.local with resolved backend port
# ===================================================================
$frontendEnvLocal = Join-Path $FRONTEND_DIR ".env.local"
Set-DotEnvKey -FilePath $frontendEnvLocal -Key "VITE_API_URL" `
    -Value "http://localhost:$resolvedBackendPort/api/v1"
Write-Ok "Synced .env.local: VITE_API_URL=http://localhost:$resolvedBackendPort/api/v1"
Write-Host ""

# ===================================================================
#  STEP 8  -  Launch servers
# ===================================================================
Write-Host "  =============================================" -ForegroundColor Green
Write-Host "    Starting HealthCentral ..." -ForegroundColor Green
Write-Host "  =============================================" -ForegroundColor Green
Write-Host ""
Write-Host "    Backend API:  http://localhost:$resolvedBackendPort" -ForegroundColor Cyan
Write-Host "    Frontend:     http://localhost:$resolvedFrontendPort" -ForegroundColor Cyan
Write-Host "    API Docs:     http://localhost:$resolvedBackendPort/docs" -ForegroundColor Cyan
Write-Host ""

# We need to pass the current PATH to background jobs so they can find npm/node.
$currentPath = $env:PATH
$npmPath     = (Get-Command npm -ErrorAction SilentlyContinue).Source | Split-Path
$frontendLog = Join-Path $ROOT_DIR "logs\dev-frontend.log"

# -- Backend (background process) --
$backendProc = Start-Process -FilePath $venvPython `
    -ArgumentList "-m", "uvicorn", "main:app", "--reload", "--host", "127.0.0.1", "--port", "$resolvedBackendPort" `
    -WorkingDirectory $BACKEND_DIR `
    -WindowStyle Hidden `
    -PassThru

# Give backend a head start
Start-Sleep -Seconds 2

# -- Frontend (background process) --
# Launch Vite via node + vite.js directly to avoid .cmd wrapper issues on Windows.
$frontendProc = Start-FrontendDevServer `
    -NodeExePath $nodeExe `
    -FrontendViteScriptPath $viteScript `
    -Port $resolvedFrontendPort `
    -WorkingDirectory $FRONTEND_DIR `
    -LogPath $frontendLog

$bPid = $backendProc.Id
$fPid = $frontendProc.Id
Write-Ok "Backend  started  [PID $bPid]"
Write-Ok "Frontend started  [PID $fPid]"
Write-Status "Frontend log: $frontendLog"
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

    if ($frontendProc.HasExited) {
        $ec = $frontendProc.ExitCode
        Write-Err "Frontend exited during startup [exit code $ec]."
        Write-LogTail -LogPath $frontendLog -Label "Frontend log"
        Read-Host "  Press Enter to exit"
        exit 1
    }

    try {
        $response = Invoke-WebRequest -Uri "http://localhost:$resolvedFrontendPort" `
                        -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            Write-Ok "Servers are ready!"
            Write-Host ""
            Start-Process "http://localhost:$resolvedFrontendPort"
            $opened = $true
            break
        }
    } catch { }
}

if (-not $opened) {
    Write-Warn "Servers are still starting. Opening browser anyway ..."
    Start-Process "http://localhost:$resolvedFrontendPort"
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
    $frontendRestartCount = 0
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
                -ArgumentList "-m", "uvicorn", "main:app", "--reload", "--host", "127.0.0.1", "--port", "$resolvedBackendPort" `
                -WorkingDirectory $BACKEND_DIR `
                -WindowStyle Hidden `
                -PassThru
            $bPid = $backendProc.Id
            Write-Ok "Backend restarted [PID $bPid]"
        }
        if ($frontendDead) {
            $ec = $frontendProc.ExitCode
            Write-Warn "Frontend stopped unexpectedly [exit code $ec]. Restarting ..."
            Write-LogTail -LogPath $frontendLog -Label "Frontend log"
            $frontendRestartCount++
            if ($frontendRestartCount -ge 3) {
                Write-Err "Frontend failed repeatedly. See $frontendLog"
                break
            }
            $frontendProc = Start-FrontendDevServer `
                -NodeExePath $nodeExe `
                -FrontendViteScriptPath $viteScript `
                -Port $resolvedFrontendPort `
                -WorkingDirectory $FRONTEND_DIR `
                -LogPath $frontendLog
            $fPid = $frontendProc.Id
            Write-Ok "Frontend restarted [PID $fPid]"
        } else {
            $frontendRestartCount = 0
        }
    }
} finally {
    Stop-Servers
}
