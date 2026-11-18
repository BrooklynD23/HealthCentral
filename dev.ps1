<#
.SYNOPSIS
    Asclexis Development Server Startup Script
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

# ---------------------------------------------------------------------------
# Launcher log (WIN-LAUNCHER-LOG): every run writes a transcript of what this window showed to
# logs\launcher\dev-<yyyyMMdd-HHmmss>.log and keeps the newest 20. It holds screen output only
# (status lines, tool output, log tails), never .env contents. logs\ is gitignored.
# ---------------------------------------------------------------------------
$LAUNCHER_LOG_DIR  = Join-Path $ROOT_DIR "logs\launcher"
$LAUNCHER_LOG_KEEP = 20
$script:LauncherLogPath = $null

function Remove-OldLauncherLogs {
    try {
        @(Get-ChildItem -LiteralPath $LAUNCHER_LOG_DIR -Filter "dev-*.log" -File -ErrorAction SilentlyContinue |
            Sort-Object Name -Descending |
            Select-Object -Skip $LAUNCHER_LOG_KEEP) |
            ForEach-Object { Remove-Item -LiteralPath $_.FullName -Force -ErrorAction SilentlyContinue }
    } catch { }
}

function Start-LauncherLog {
    try {
        New-Item -ItemType Directory -Path $LAUNCHER_LOG_DIR -Force -ErrorAction Stop | Out-Null
        $path = Join-Path $LAUNCHER_LOG_DIR ("dev-{0}.log" -f (Get-Date -Format "yyyyMMdd-HHmmss"))
        Start-Transcript -Path $path -ErrorAction Stop | Out-Null
        $script:LauncherLogPath = $path
        Remove-OldLauncherLogs
    } catch {
        $script:LauncherLogPath = $null   # logging must never stop the launcher
    }
}

function Stop-LauncherLog {
    if (-not $script:LauncherLogPath) { return }
    try { Stop-Transcript | Out-Null } catch { }
    $script:LauncherLogPath = $null
}

function Write-LauncherLogHint {
    if ($script:LauncherLogPath) { Write-Status "Launcher log: $($script:LauncherLogPath)" }
}

# Every error exit that waits for a key goes through here so the log path is the last thing shown.
function Read-LauncherExit {
    Write-LauncherLogHint
    Read-Host "  Press Enter to exit"
}

Start-LauncherLog
Write-LauncherLogHint
try {
    $gitHead = $null
    if (Get-Command git -ErrorAction SilentlyContinue) {
        $gitHead = "$(& git -C $ROOT_DIR rev-parse --short HEAD 2>$null)".Trim()
    }
    if ($gitHead) { Write-Status "Git HEAD: $gitHead" }
} catch { }

# The rest of the script runs inside this try so the transcript is stopped on every exit
# (exit, Ctrl+C, an uncaught error). The matching finally is the last statement in the file.
try {

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
    # Windows PowerShell 5.1 joins -ArgumentList items with spaces and does not quote them, so a repo path
    # with a space ("...\Github Repo\...") reached node as two arguments. Quote the script path.
    return Start-Process -FilePath $NodeExePath `
        -ArgumentList "`"$FrontendViteScriptPath`"", "--port", "$Port", "--strictPort" `
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
$host.UI.RawUI.WindowTitle = "Asclexis"
Write-Host ""
Write-Host "  =============================================" -ForegroundColor Magenta
Write-Host "    Asclexis  -  Development Server" -ForegroundColor Magenta
Write-Host "  =============================================" -ForegroundColor Magenta
Write-Host ""

# ===================================================================
#  STEP 1  -  Check prerequisites (Python, Node, npm)
# ===================================================================
Write-Host "  --- Checking prerequisites ---" -ForegroundColor DarkGray

# -- Python --
function Find-Python311Command {
    $userPython = Join-Path $env:LOCALAPPDATA "Programs\Python\Python311\python.exe"
    foreach ($cmd in @("python", "python3", "py", $userPython)) {
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
        Read-LauncherExit
        exit 1
    }
    $answer = Read-Host "  Python 3.11+ was not found. Install Python 3.11 automatically with winget? [Y/n]"
    if ($answer -and $answer.Trim() -match '^[Nn]') {
        Write-PythonManualInstallHelp
        Read-LauncherExit
        exit 1
    }
    Write-Status "Installing Python 3.11 via winget (this may take a few minutes) ..."
    & winget install --id Python.Python.3.11 --exact --source winget --scope user --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) {
        if ($LASTEXITCODE -eq -1978334964 -or $LASTEXITCODE -eq 1602) {
            Write-Err "The Python installer was cancelled (an admin prompt may have been declined or hidden behind another window). Re-run dev.bat, or install Python 3.11 from https://python.org/downloads with 'Add Python to PATH' checked."
        } else {
            Write-Err "winget install failed (exit code $LASTEXITCODE)."
        }
        Write-PythonManualInstallHelp
        Read-LauncherExit
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
        Read-LauncherExit
        exit 1
    }
}

# -- Node.js --
Write-Status "Looking for Node.js 22.12+ ..."
$nodeOk = $false
$nodeExe = $null
try {
    $nodeVersion = & node --version 2>&1
    if ($nodeVersion -match "v(\d+\.\d+\.\d+)") {
        if ([version]$Matches[1] -ge [version]"22.12.0") {
            Write-Ok "Found Node.js $nodeVersion"
            $nodeExe = (Get-Command node -ErrorAction Stop).Source
            $nodeOk = $true
        } else {
            Write-Err "Found Node.js $nodeVersion - version 22.12+ is required; this version is too old and will not be used."
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
    Write-Err "Node.js 22.12+ is required but not found."
    Write-Host ""
    Write-Host "    Download it from:  https://nodejs.org  (Node.js 24 LTS recommended)" -ForegroundColor White
    Write-Host ""
    Read-LauncherExit
    exit 1
}

# -- npm --
Write-Status "Looking for npm ..."
try {
    $npmVersion = & npm --version 2>&1
    Write-Ok "Found npm v$npmVersion"
} catch {
    Write-Err "npm is required but not found (it ships with Node.js)."
    Read-LauncherExit
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
        Read-LauncherExit
        exit 1
    }
    Write-Ok "Virtual environment created"
} else {
    Write-Ok "Virtual environment exists"
}

$venvPython = Join-Path $VENV_DIR "Scripts\python.exe"
$venvPip    = Join-Path $VENV_DIR "Scripts\pip.exe"

# ===================================================================
#  STEP 3  -  Install Python dependencies (SQLCipher first; never silently off)
# ===================================================================
Write-Status "Installing Python dependencies ..."

# Upgrade pip quietly first
& $venvPython -m pip install --upgrade pip --quiet 2>&1 | Out-Null

# SQLCipher comes first, from one pinned, hash-checked wheel (requirements-sqlcipher-win.txt),
# and must pass a file probe. If it does not, this launcher stops: it never turns encryption
# off by itself. HC_ALLOW_UNENCRYPTED=1 is the only override (development only).
$sqlcipherAvailable = $false
$allowUnencrypted = ($env:HC_ALLOW_UNENCRYPTED -eq "1")
$requirementsFile = Join-Path $BACKEND_DIR "requirements.txt"

# llama-cpp-python: install the pinned prebuilt CPU wheel first, so no C++ toolchain is needed.
# The source build (and the compiler check below) applies only when this step is skipped
# (CMAKE_ARGS set) or finds no wheel for this platform.
$llamaPin = $null
$llamaPinLine = Get-Content $requirementsFile | Where-Object { $_ -match '^\s*llama-cpp-python==' } | Select-Object -First 1
if ($llamaPinLine -match '^\s*llama-cpp-python==([^\s;#]+)') { $llamaPin = $Matches[1] }
$llamaWheelOk = $false
if ($env:CMAKE_ARGS) {
    Write-Status "CMAKE_ARGS is set: skipping the prebuilt llama-cpp-python wheel (pip builds it from source)"
} elseif ($llamaPin) {
    Write-Status "Installing llama-cpp-python $llamaPin from the prebuilt wheel index ..."
    & $venvPip install --only-binary=llama-cpp-python --index-url "https://abetlen.github.io/llama-cpp-python/whl/cpu" "llama-cpp-python==$llamaPin" --no-deps 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        $llamaWheelOk = $true
        Write-Ok "llama-cpp-python $llamaPin is ready (prebuilt wheel)"
    } else {
        Write-Warn "No prebuilt llama-cpp-python $llamaPin wheel was installed (no wheel for this platform, or the index is unreachable); pip will try a source build"
    }
}

# No wheel and no C++ compiler: a source build cannot succeed. LLM_PROVIDER=ollama does not need llama-cpp-python.
$nollamaReqs = $null
if (-not $llamaWheelOk -and -not (Get-Command cl.exe -ErrorAction SilentlyContinue)) {
    $llmProvider = "$env:LLM_PROVIDER".Trim().ToLower()
    foreach ($cfg in @($ENV_FILE, $ENV_EXAMPLE)) {
        if (-not $llmProvider -and (Test-Path $cfg)) {
            $providerLine = Get-Content $cfg | Where-Object { $_ -match '^\s*LLM_PROVIDER\s*=' } | Select-Object -Last 1
            if ($providerLine) { $llmProvider = (($providerLine -split '=', 2)[1] -replace '#.*$', '').Trim().Trim('"', "'").ToLower() }
        }
    }
    if ($llmProvider -eq "ollama") {
        Write-Warn "llama-cpp-python skipped: no C++ compiler (cl.exe); LLM_PROVIDER=ollama does not need it"
        $nollamaReqs = Join-Path $env:TEMP "hc-requirements-nollama.txt"
        Get-Content $requirementsFile | Where-Object { $_ -notmatch '^\s*llama-cpp-python' } | Set-Content $nollamaReqs
        $requirementsFile = $nollamaReqs
    } else {
        Write-Err "No prebuilt llama-cpp-python wheel could be installed, and no C++ compiler (cl.exe) was found on PATH to build it."
        Write-Err "Install Visual Studio Build Tools with the 'Desktop development with C++' workload:"
        Write-Err "  https://visualstudio.microsoft.com/visual-cpp-build-tools/"
        Write-Err "Then open a new window and run dev.bat again. Or set LLM_PROVIDER=ollama in src\backend\.env."
        Read-LauncherExit
        exit 1
    }
}

# -- SQLCipher: pinned wheel, hashes required, binary only, then a file probe --
$sqlcipherReqs = Join-Path $BACKEND_DIR "requirements-sqlcipher-win.txt"
$probeScript   = Join-Path $ROOT_DIR "scripts\check_sqlcipher.py"
Write-Status "Installing SQLCipher (encrypted vaults) from the pinned wheel ..."
$sqlcipherOutput = @(& $venvPip install --only-binary=:all: --no-deps --require-hashes -r $sqlcipherReqs 2>&1)
$sqlcipherExit   = $LASTEXITCODE
if ($sqlcipherExit -eq 0) {
    Write-Status "Checking that SQLCipher really encrypts a file ..."
    $sqlcipherOutput = @(& $venvPython $probeScript --file-probe 2>&1)
    $sqlcipherExit   = $LASTEXITCODE
}
if ($sqlcipherExit -eq 0) {
    $sqlcipherAvailable = $true
    Write-Ok "SQLCipher is ready (file probe passed)"
} elseif ($allowUnencrypted) {
    Write-Host ""
    Write-Host "  ============================================================" -ForegroundColor Red
    Write-Host "   HC_ALLOW_UNENCRYPTED=1: SQLCipher could not be set up." -ForegroundColor Red
    Write-Host "   Your health data will NOT be encrypted on this computer." -ForegroundColor Red
    Write-Host "   Development only. Do not store real patient data." -ForegroundColor Red
    Write-Host "  ============================================================" -ForegroundColor Red
    Write-Host ""
    $filteredReqs = Join-Path $env:TEMP "hc-requirements-nosqlcipher.txt"
    Get-Content $requirementsFile | Where-Object { $_ -notmatch '^\s*sqlcipher' } | Set-Content $filteredReqs
    if ($nollamaReqs) { Remove-Item $nollamaReqs -Force -ErrorAction SilentlyContinue }
    $nollamaReqs = $filteredReqs
    $requirementsFile = $filteredReqs
} else {
    Write-Err "SQLCipher could not be installed or did not pass its check. Last output:"
    $sqlcipherOutput | Select-Object -Last 12 | ForEach-Object { Write-Host "    $_" -ForegroundColor DarkRed }
    Write-Err "It needs 64-bit Python 3.11 (the pinned wheel is cp311 win_amd64) and access to pypi.org."
    Write-Err "dev.bat stopped so your health data is never stored unencrypted; .env was not changed."
    Write-Err "For development only, set HC_ALLOW_UNENCRYPTED=1 to continue without encryption."
    Read-LauncherExit
    exit 1
}

Push-Location $BACKEND_DIR
$pipOutput = & $venvPip install -r $requirementsFile 2>&1
$pipExit   = $LASTEXITCODE
Pop-Location

if ($pipExit -ne 0) {
    Write-Err "Failed to install Python dependencies. Output:"
    $pipOutput | ForEach-Object { Write-Host "    $_" -ForegroundColor DarkRed }
    Read-LauncherExit
    exit 1
} else {
    Write-Ok "Python dependencies installed"
}
if ($nollamaReqs) { Remove-Item $nollamaReqs -Force -ErrorAction SilentlyContinue }

# Embedding model: document chunks need it. The backend loads it offline and never downloads it;
# this step is the one place it is fetched (about 88 MB, once). Already installed: no network.
Write-Status "Checking the embedding model ..."
Push-Location $BACKEND_DIR
& $venvPython "scripts\download_models.py" embedding 2>&1 | ForEach-Object { Write-Host "    $_" -ForegroundColor DarkGray }
$embeddingExit = $LASTEXITCODE
Pop-Location
if ($embeddingExit -ne 0) {
    Write-Err "The embedding model is missing and could not be fetched (it needs internet once, about 88 MB)."
    Write-Err "To retry, run from src\backend: $venvPython scripts\download_models.py embedding"
    Read-LauncherExit
    exit 1
}
Write-Ok "Embedding model is ready"

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
            "DATABASE_ENCRYPTION_REQUIRED=true"
        )
        $defaultEnv -join "`r`n" | Set-Content $ENV_FILE
        Write-Ok "Created default .env"
    }
}

# SQLCipher passed its file probe: encryption is required (an older .env may say false).
# Only HC_ALLOW_UNENCRYPTED=1 (see STEP 3) ever writes false.
if ($sqlcipherAvailable) {
    $envContent = Get-Content $ENV_FILE -Raw
    $wasFalse = ($envContent -match "(?im)^\s*DATABASE_ENCRYPTION_REQUIRED\s*=\s*false")
    Set-DotEnvKey -FilePath $ENV_FILE -Key "DATABASE_ENCRYPTION_REQUIRED" -Value "true"
    if ($wasFalse) {
        Write-Ok "Set DATABASE_ENCRYPTION_REQUIRED=true (SQLCipher file probe passed)"
    }
} else {
    Set-DotEnvKey -FilePath $ENV_FILE -Key "DATABASE_ENCRYPTION_REQUIRED" -Value "false"
    Write-Warn "Set DATABASE_ENCRYPTION_REQUIRED=false (HC_ALLOW_UNENCRYPTED=1): vaults will NOT be encrypted"
}

# Match backend gate: OCR_ENABLED is meaningful only when an OCR engine exists:
# bundled RapidOCR (checked first, in the backend venv) or Tesseract on PATH.
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
    # The probe loads the OCR engine; it takes several seconds on a first run.
    Write-Status "Checking for the bundled RapidOCR engine ..."
    $rapidocrResolved = $false
    Push-Location $BACKEND_DIR
    try {
        & $venvPython -c "from modules.extract import rapidocr_ready; raise SystemExit(0 if rapidocr_ready() else 1)" 2>&1 | Out-Null
        $rapidocrResolved = ($LASTEXITCODE -eq 0)
    } catch {
        $rapidocrResolved = $false
    } finally {
        Pop-Location
    }
    Set-DotEnvKey -FilePath $ENV_FILE -Key "OCR_ENABLED" -Value $(if ($rapidocrResolved -or $tesseractResolved) { "true" } else { "false" })
    if ($rapidocrResolved -and $tesseractResolved) {
        Write-Ok "Synced .env: OCR_ENABLED=true (RapidOCR and Tesseract found)"
    } elseif ($rapidocrResolved) {
        Write-Ok "Synced .env: OCR_ENABLED=true (RapidOCR found)"
    } elseif ($tesseractResolved) {
        Write-Ok "Synced .env: OCR_ENABLED=true (Tesseract on PATH)"
    } else {
        Write-Warn "Synced .env: OCR_ENABLED=false (neither RapidOCR nor Tesseract found - re-run dev.ps1 after installing dependencies)"
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

# Decides whether frontend dependencies must be (re)installed.
# Returns "" when the tree is current, otherwise the reason:
#   "missing"          - no node_modules
#   "incomplete"       - node_modules without the Vite binary
#   "lockfile-changed" - package-lock.json is not the one node_modules was installed from
function Get-FrontendInstallReason {
    param([string]$FrontendDir)
    $modules = Join-Path $FrontendDir "node_modules"
    if (-not (Test-Path -LiteralPath $modules)) { return "missing" }
    if (-not (Test-Path -LiteralPath (Join-Path $modules ".bin\vite.cmd")) -or
        -not (Test-Path -LiteralPath (Join-Path $modules "vite\bin\vite.js"))) { return "incomplete" }
    $lockFile = Join-Path $FrontendDir "package-lock.json"
    $marker   = Join-Path $modules ".asclexis-lockfile.sha256"
    if (-not (Test-Path -LiteralPath $lockFile) -or -not (Test-Path -LiteralPath $marker)) { return "lockfile-changed" }
    $current  = (Get-FileHash -LiteralPath $lockFile -Algorithm SHA256).Hash
    $recorded = "$(Get-Content -LiteralPath $marker -TotalCount 1)".Trim()
    if ($current -ne $recorded) { return "lockfile-changed" }
    return ""
}

# Path of the npm application (npm.cmd / npm.exe), or "" when there is none.
# Not "& npm": PowerShell resolves that to the npm.ps1 shim, which drops the first
# character of its arguments when it is called through "&" (npm 11: `Unknown command: "pm"`).
function Get-NpmApplicationPath {
    $app = Get-Command npm -CommandType Application -ErrorAction SilentlyContinue |
        Where-Object { $_.Extension -in '.cmd', '.exe' } | Select-Object -First 1
    if ($app) { return $app.Source }
    return ""
}

# Runs `npm ci` and records the lockfile hash only when it succeeded and Vite is present.
# Returns $true on success. On failure prints why and returns $false; nothing is recorded.
function Install-FrontendDependencies {
    param([string]$FrontendDir)
    $modules = Join-Path $FrontendDir "node_modules"
    $marker  = Join-Path $modules ".asclexis-lockfile.sha256"
    # npm ci empties node_modules. If node_modules is a link, that would empty the folder it points to.
    $modulesItem = Get-Item -LiteralPath $modules -Force -ErrorAction SilentlyContinue
    if ($modulesItem -and $modulesItem.LinkType) {
        Write-Err "src\frontend\node_modules is a link to another folder. Nothing was changed."
        Write-Err "Remove the link (not the folder it points to) and run again."
        return $false
    }
    # The old record goes first: a failed or interrupted install must never look current.
    Remove-Item -LiteralPath $marker -Force -ErrorAction SilentlyContinue
    # Hash the lockfile npm is about to install, not the one on disk when npm has finished.
    $lockHash = ""
    $lockFile = Join-Path $FrontendDir "package-lock.json"
    if (Test-Path -LiteralPath $lockFile) { $lockHash = (Get-FileHash -LiteralPath $lockFile -Algorithm SHA256).Hash }
    $npmCommand = Get-NpmApplicationPath
    $npmExit = 1
    $npmOutput = "npm was not found on PATH."
    if ($npmCommand -ne "") {
        $pushed = $false
        try {
            # Stop: if the folder cannot be entered, npm must not run in whatever folder we are in.
            Push-Location -LiteralPath $FrontendDir -ErrorAction Stop
            $pushed = $true
            $npmOutput = & $npmCommand ci 2>&1
            $npmExit = $LASTEXITCODE
        } catch {
            $npmOutput = $_.Exception.Message
            $npmExit = 1
        }
        if ($pushed) { Pop-Location }
    }
    if ($npmExit -ne 0) {
        Write-Err "npm ci failed (exit code $npmExit). Frontend dependencies are not installed."
        $npmOutput | Select-Object -Last 15 | ForEach-Object { Write-Host "      $_" }
        Write-Err "Check your internet connection, close other Asclexis windows, and run again."
        return $false
    }
    if (-not (Test-Path -LiteralPath (Join-Path $modules ".bin\vite.cmd")) -or
        -not (Test-Path -LiteralPath (Join-Path $modules "vite\bin\vite.js"))) {
        Write-Err "npm install succeeded but Vite was not found."
        Write-Err "Try deleting src\frontend\node_modules and running again."
        return $false
    }
    try {
        Set-Content -LiteralPath $marker -Value $lockHash -Encoding ASCII -ErrorAction Stop
    } catch {
        # The tree itself is correct, so the app may start; only the record is missing.
        Write-Warn "Could not record the installed version; the next start will reinstall frontend dependencies."
    }
    return $true
}

$installReason = Get-FrontendInstallReason -FrontendDir $FRONTEND_DIR
if ($installReason -ne "") {
    switch ($installReason) {
        "missing"          { Write-Status "Installing frontend dependencies (first-time setup) ..." }
        "incomplete"       { Write-Warn "node_modules exists but looks incomplete. Reinstalling ..." }
        "lockfile-changed" { Write-Status "Frontend dependencies changed since the last install. Reinstalling ..." }
    }
    if (-not (Install-FrontendDependencies -FrontendDir $FRONTEND_DIR)) {
        Read-LauncherExit
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

# An Asclexis backend or frontend left running from THIS folder (an earlier dev.bat) can hold a
# profile vault open; moving to the next free port would hide it. Stop and say so. Other
# programs on these ports keep the free-the-port / next-free-port behaviour below.
function Find-AsclexisFromThisFolder {
    $found = @{}
    $root = $ROOT_DIR.TrimEnd('\').ToLower()
    foreach ($range in @((8000..8010), (3000..3010))) {
        foreach ($port in $range) {
            foreach ($procId in (Get-ListenerPidsForPort -Port $port)) {
                $proc = Get-CimInstance Win32_Process -Filter "ProcessId = $procId" -ErrorAction SilentlyContinue
                $cmd = "$($proc.CommandLine)".ToLower()
                if ($cmd -and $cmd.Contains($root)) { $found[[int]$procId] = $port }
            }
        }
    }
    return @($found.Keys | ForEach-Object { [pscustomobject]@{ Pid = [int]$_; Port = [int]$found[$_] } })
}
# The backend records the PID of the process that serves requests (src/backend/core/worker_pidfile.py).
# That process can outlive this launcher (the venv python.exe is a stub, and uvicorn --reload spawns
# the worker as a child), holding a profile vault open with no listening port, so the port check
# above cannot see it. The file lives in logs\, outside data\, so no backup picks it up.
$workerPidFile  = Join-Path $ROOT_DIR "logs\dev-backend.pid"
$runStartedUnix = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds() / 1000.0

function Read-WorkerPidFile {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) { return $null }
    try {
        $data = (Get-Content -LiteralPath $Path -Raw -ErrorAction Stop) | ConvertFrom-Json -ErrorAction Stop
        if (-not $data.pid -or -not $data.started_unix) { return $null }
        return [pscustomobject]@{ pid = [int]$data.pid; started_unix = [double]$data.started_unix }
    } catch { return $null }
}

# True only for a live Python process whose command line is uvicorn or a multiprocessing spawn
# (the --reload worker), created no later than the moment the PID file was written. Windows reuses
# PIDs, so a live PID alone is never enough to act on.
function Test-AsclexisWorkerProcess {
    param([int]$ProcessId, [double]$StartedUnix)
    $proc = Get-CimInstance Win32_Process -Filter "ProcessId = $ProcessId" -ErrorAction SilentlyContinue
    if (-not $proc) { return $false }
    if ("$($proc.Name)".ToLower() -notmatch '^pythonw?(\d+(\.\d+)*)?\.exe$') { return $false }
    $cmd = "$($proc.CommandLine)".ToLower()
    if ($cmd -notmatch 'uvicorn|spawn_main|main:app') { return $false }
    $written = [DateTimeOffset]::FromUnixTimeMilliseconds([long]($StartedUnix * 1000)).UtcDateTime
    if ($proc.CreationDate -and $proc.CreationDate.ToUniversalTime() -gt $written.AddSeconds(2)) { return $false }
    return $true
}

# uvicorn --reload runs the worker as a child of a reloader, and the venv python.exe is a stub that
# starts the real python, so `taskkill /PID <worker> /T` leaves the reloader (and stub) alive and the
# reloader keeps the port. Child and Parent are Win32_Process rows. True only for a real parent (its PID
# is the child's ParentProcessId), a python process whose command line is uvicorn, a multiprocessing
# spawn or the venv, that was created no later than the child (Windows reuses PIDs, and a reused PID is
# created after the child). Never cmd, powershell, explorer or anything that is not python.
function Test-AsclexisBackendAncestor {
    param($Child, $Parent)
    if (-not $Child -or -not $Parent) { return $false }
    if ([int]$Parent.ProcessId -le 4) { return $false }
    if ([int]$Child.ParentProcessId -ne [int]$Parent.ProcessId) { return $false }
    if ("$($Parent.Name)".ToLower() -notmatch '^pythonw?(\d+(\.\d+)*)?\.exe$') { return $false }
    $cmd = "$($Parent.CommandLine)".ToLower()
    if ($cmd -notmatch 'uvicorn|spawn_main|main:app' -and -not $cmd.Contains($VENV_DIR.TrimEnd('\').ToLower())) { return $false }
    if (-not $Parent.CreationDate -or -not $Child.CreationDate) { return $false }
    if ($Parent.CreationDate -gt $Child.CreationDate) { return $false }
    return $true
}

# The top-most live ancestor of a verified backend process that Test-AsclexisBackendAncestor accepts
# (the worker itself when there is none). This is the PID a taskkill /T must target.
function Get-AsclexisBackendRoot {
    param([int]$ProcessId)
    $rootId = $ProcessId
    $child = Get-CimInstance Win32_Process -Filter "ProcessId = $ProcessId" -ErrorAction SilentlyContinue
    $seen = @{}
    $seen[$ProcessId] = $true
    for ($depth = 0; $child -and $depth -lt 8; $depth++) {
        $parentId = [int]$child.ParentProcessId
        if ($parentId -le 4 -or $seen.ContainsKey($parentId)) { break }
        $seen[$parentId] = $true
        $parent = Get-CimInstance Win32_Process -Filter "ProcessId = $parentId" -ErrorAction SilentlyContinue
        if (-not (Test-AsclexisBackendAncestor -Child $child -Parent $parent)) { break }
        $rootId = $parentId
        $child = $parent
    }
    return $rootId
}

function Format-AsclexisTaskkillLine {
    param([int[]]$ProcessIds)
    $pidArgs = ($ProcessIds | ForEach-Object { "/PID $_" }) -join " "
    return "taskkill $pidArgs /T /F"
}

# Everything left running from this folder: the backend tree root of the verified recorded worker, and
# each listener on the backend/frontend port ranges that Find-AsclexisFromThisFolder attributes to this
# folder (a python listener is walked up to its root; node is the frontend). One row per PID.
function Get-AsclexisLeftovers {
    param($Worker)
    $rows = [ordered]@{}
    function Add-Row {
        param([int]$ProcessId, [string]$Role)
        # String keys: an int key on an ordered dictionary is read as a position, not a key.
        if ($rows.Contains("$ProcessId")) { return }
        $proc = Get-CimInstance Win32_Process -Filter "ProcessId = $ProcessId" -ErrorAction SilentlyContinue
        $rows["$ProcessId"] = [pscustomobject]@{ Pid = $ProcessId; Image = "$($proc.Name)"; Role = $Role }
    }
    if ($Worker) {
        Add-Row -ProcessId (Get-AsclexisBackendRoot -ProcessId $Worker.pid) -Role "backend (uvicorn tree root; worker PID $($Worker.pid))"
    }
    foreach ($l in @(Find-AsclexisFromThisFolder)) {
        $proc = Get-CimInstance Win32_Process -Filter "ProcessId = $($l.Pid)" -ErrorAction SilentlyContinue
        if ("$($proc.Name)".ToLower() -match '^pythonw?(\d+(\.\d+)*)?\.exe$') {
            Add-Row -ProcessId (Get-AsclexisBackendRoot -ProcessId $l.Pid) -Role "backend (uvicorn tree root; listening on port $($l.Port))"
        } elseif ("$($proc.Name)".ToLower() -eq "node.exe") {
            Add-Row -ProcessId $l.Pid -Role "frontend dev server (listening on port $($l.Port))"
        } else {
            Add-Row -ProcessId $l.Pid -Role "listening on port $($l.Port)"
        }
    }
    return @($rows.Values)
}

# Process and port snapshot for the launcher log, written when the launcher refuses to start: every
# python.exe and node.exe, and every listener on the backend/frontend port ranges with its owning
# PID and command line. Best effort: a failure here never changes the refusal.
function Write-LauncherSnapshot {
    Write-Host "  --- Process and port snapshot (also in the launcher log) ---" -ForegroundColor DarkGray
    try {
        foreach ($img in @("python.exe", "node.exe")) {
            Write-Host "  tasklist /fi `"imagename eq $img`"" -ForegroundColor DarkGray
            foreach ($line in @(& tasklist.exe /fi "imagename eq $img" 2>&1)) { Write-Host "    $line" -ForegroundColor DarkGray }
        }
        $ports = @(8000..8010) + @(3000..3010)
        $conns = @(Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Where-Object { $ports -contains [int]$_.LocalPort })
        if ($conns.Count -eq 0) {
            foreach ($port in $ports) {
                foreach ($id in (Get-ListenerPidsForPort -Port $port)) { $conns += [pscustomobject]@{ LocalPort = $port; OwningProcess = $id } }
            }
        }
        Write-Host "  listeners on 8000-8010 and 3000-3010:" -ForegroundColor DarkGray
        if ($conns.Count -eq 0) { Write-Host "    none" -ForegroundColor DarkGray }
        foreach ($c in ($conns | Sort-Object LocalPort, OwningProcess)) {
            $proc = Get-CimInstance Win32_Process -Filter "ProcessId = $([int]$c.OwningProcess)" -ErrorAction SilentlyContinue
            Write-Host "    port $($c.LocalPort)  PID $($c.OwningProcess)  $($proc.Name)  $($proc.CommandLine)" -ForegroundColor DarkGray
        }
    } catch {
        Write-Host "    (snapshot failed: $($_.Exception.Message))" -ForegroundColor DarkGray
    }
}

# Stop the recorded worker's whole tree (its root, found by Get-AsclexisBackendRoot) if the worker is
# verifiably this run's Asclexis worker, then remove the file. A tree that does not die keeps its file,
# so the next start refuses and says why.
function Stop-RecordedWorker {
    param([string]$Path, [double]$NotBeforeUnix = 0)
    $worker = Read-WorkerPidFile -Path $Path
    if (-not $worker) { return }
    if ($worker.started_unix -lt $NotBeforeUnix) { return }
    if (Test-AsclexisWorkerProcess -ProcessId $worker.pid -StartedUnix $worker.started_unix) {
        $killId = Get-AsclexisBackendRoot -ProcessId $worker.pid
        & taskkill.exe /PID $killId /T /F 2>&1 | Out-Null
        for ($i = 0; $i -lt 10; $i++) {
            if (-not (Get-Process -Id $killId -ErrorAction SilentlyContinue) -and
                -not (Get-Process -Id $worker.pid -ErrorAction SilentlyContinue)) { break }
            Start-Sleep -Milliseconds 500
        }
        if ((Get-Process -Id $killId -ErrorAction SilentlyContinue) -or (Get-Process -Id $worker.pid -ErrorAction SilentlyContinue)) {
            Write-Warn "Backend worker PID $($worker.pid) did not stop. Run: taskkill /PID $killId /T /F"
            return
        }
    }
    Remove-Item -LiteralPath $Path -Force -ErrorAction SilentlyContinue
}

# One refusal for everything this folder left running (a backend tree, a frontend node), with one
# taskkill line. Checked before any port is picked or freed.
$worker = Read-WorkerPidFile -Path $workerPidFile
$liveWorker = $null
if ($worker -and (Test-AsclexisWorkerProcess -ProcessId $worker.pid -StartedUnix $worker.started_unix)) { $liveWorker = $worker }
$leftovers = @(Get-AsclexisLeftovers -Worker $liveWorker)
if ($leftovers.Count -gt 0) {
    Write-LauncherSnapshot
    $pidList = ($leftovers | ForEach-Object { $_.Pid }) -join ", "
    Write-Err "Asclexis is already running from this folder (PID $pidList). Close it first, or run:"
    foreach ($row in $leftovers) { Write-Err "    PID $($row.Pid)  $($row.Image)  $($row.Role)" }
    Write-Err "  $(Format-AsclexisTaskkillLine -ProcessIds ($leftovers | ForEach-Object { $_.Pid }))"
    Write-Err "A leftover copy can keep a profile vault open, so this launcher will not start a second one."
    Read-LauncherExit
    exit 1
}
if (Test-Path -LiteralPath $workerPidFile) {
    Remove-Item -LiteralPath $workerPidFile -Force -ErrorAction SilentlyContinue
    Write-Status "Removed a stale worker PID file (the recorded process is gone or is not the Asclexis backend)."
}

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
Write-Host "    Starting Asclexis ..." -ForegroundColor Green
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
$backendLog    = Join-Path $ROOT_DIR "logs\dev-backend.log"
$backendErrLog = Join-Path $ROOT_DIR "logs\dev-backend.err.log"

# Start uvicorn with stdout and stderr redirected to files (PowerShell cannot
# send both streams to one file). Shared by STEP 8 and the STEP 10 restart.
# --no-access-log: the access log records full request lines (search text in
# query strings) and these logs are plaintext on disk.
function Start-BackendDevServer {
    $logDir = Split-Path -Parent $backendLog
    if (-not (Test-Path -LiteralPath $logDir)) {
        New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    }
    # The backend worker writes its PID here (inherited by the child process).
    $env:HC_WORKER_PIDFILE = $workerPidFile
    return Start-Process -FilePath $venvPython `
        -ArgumentList "-m", "uvicorn", "main:app", "--reload", "--no-access-log", "--host", "127.0.0.1", "--port", "$resolvedBackendPort" `
        -WorkingDirectory $BACKEND_DIR `
        -WindowStyle Hidden `
        -RedirectStandardOutput $backendLog `
        -RedirectStandardError $backendErrLog `
        -PassThru
}

# -- Backend (background process) --
$backendProc = Start-BackendDevServer

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
Write-Status "Backend log (uvicorn writes here): $backendErrLog"
Write-Status "Backend stdout log:                  $backendLog"
Write-Host ""

# ===================================================================
#  STEP 9  -  Wait for backend and frontend to be ready, then open browser
# ===================================================================
Write-Status "Waiting for servers to be ready ..."

$maxWait = 60       # seconds
$sw      = [System.Diagnostics.Stopwatch]::StartNew()
$opened  = $false
$backendReady  = $false
$frontendReady = $false

while ($sw.Elapsed.TotalSeconds -lt $maxWait) {
    Start-Sleep -Seconds 1

    if ($frontendProc.HasExited) {
        $ec = $frontendProc.ExitCode
        Write-Err "Frontend exited during startup [exit code $ec]."
        Write-LogTail -LogPath $frontendLog -Label "Frontend log"
        # The backend is hidden and logs only to files: do not leave it on the port.
        & taskkill.exe /PID $backendProc.Id /T /F 2>&1 | Out-Null
        Stop-RecordedWorker -Path $workerPidFile -NotBeforeUnix $runStartedUnix
        Read-LauncherExit
        exit 1
    }

    if ($backendProc.HasExited) {
        $ec = $backendProc.ExitCode
        Write-Err "Backend exited during startup [exit code $ec]."
        Write-LogTail -LogPath $backendLog -Label "Backend log"
        Write-LogTail -LogPath $backendErrLog -Label "Backend error log"
        Stop-Process -Id $frontendProc.Id -Force -ErrorAction SilentlyContinue
        Read-LauncherExit
        exit 1
    }

    if (-not $backendReady) {
        try {
            $response = Invoke-WebRequest -Uri "http://127.0.0.1:$resolvedBackendPort/health" `
                            -UseBasicParsing -TimeoutSec 1 -ErrorAction SilentlyContinue
            if ($response.StatusCode -eq 200) { $backendReady = $true }
        } catch { }
    }

    if (-not $frontendReady) {
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:$resolvedFrontendPort" `
                            -UseBasicParsing -TimeoutSec 1 -ErrorAction SilentlyContinue
            if ($response.StatusCode -eq 200) { $frontendReady = $true }
        } catch { }
    }

    if ($backendReady -and $frontendReady) {
        Write-Ok "Servers are ready!"
        Write-Host ""
        Start-Process "http://localhost:$resolvedFrontendPort"
        $opened = $true
        break
    }
}

# uvicorn --reload keeps its parent alive after an import error, so
# HasExited can stay false. No /health answer within the wait is a failure.
if (-not $backendReady) {
    Write-Err "Backend did not answer /health within $maxWait seconds."
    Write-LogTail -LogPath $backendLog -Label "Backend log"
    Write-LogTail -LogPath $backendErrLog -Label "Backend error log"
    # /T kills the --reload worker child too, so it does not keep the port.
    & taskkill.exe /PID $backendProc.Id /T /F 2>&1 | Out-Null
    Stop-RecordedWorker -Path $workerPidFile -NotBeforeUnix $runStartedUnix
    Stop-Process -Id $frontendProc.Id -Force -ErrorAction SilentlyContinue
    Read-LauncherExit
    exit 1
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
Write-Host "    Asclexis is running!" -ForegroundColor Green
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
    # The worker can outlive its launcher and keep a vault open: stop it by its recorded PID.
    try { Stop-RecordedWorker -Path $workerPidFile -NotBeforeUnix $runStartedUnix } catch { }
    try {
        if (-not $frontendProc.HasExited) {
            Stop-Process -Id $frontendProc.Id -Force -ErrorAction SilentlyContinue
        }
    } catch { }
    Write-Ok "Servers stopped. Goodbye!"
}

try {
    $frontendRestartCount = 0
    $backendRestartCount  = 0
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
            Write-Warn "Backend stopped unexpectedly [exit code $ec]."
            Write-LogTail -LogPath $backendLog -Label "Backend log"
            Write-LogTail -LogPath $backendErrLog -Label "Backend error log"
            if ($backendRestartCount -ge 3) {
                Write-Err "Backend failed repeatedly. See $backendErrLog and $backendLog"
                Write-LauncherLogHint
                # exit 1 (not break): break leaves exit code 0, dev.bat then
                # closes the window before the log tail can be read.
                # The finally block still runs Stop-Servers.
                exit 1
            }
            $backendRestartCount++
            # The dead launcher's worker may still be running; stop it before a second one starts.
            Stop-RecordedWorker -Path $workerPidFile -NotBeforeUnix $runStartedUnix
            $backendProc = Start-BackendDevServer
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
                Write-LauncherLogHint
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
} finally {
    Stop-LauncherLog
}
