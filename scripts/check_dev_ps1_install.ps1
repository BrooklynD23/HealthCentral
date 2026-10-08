# Check script for the frontend install decision in dev.ps1 (STEP 5).
# Loads Get-FrontendInstallReason and Install-FrontendDependencies out of dev.ps1
# with the PowerShell parser, so the shipped code is tested and dev.ps1 never runs.
# Windows PowerShell 5.1 compatible. Temp files live under the system temp folder only.
#
#   check_dev_ps1_install.ps1                 run the 14 cases (npm is a stub .cmd file; cases 13-14 run the real npm --version)
#   check_dev_ps1_install.ps1 -Live <dir>     real decision + real `npm ci` against <dir>
param([string]$Live = "")

$ErrorActionPreference = "Stop"
$devPs1 = Join-Path (Split-Path -Parent $PSScriptRoot) "dev.ps1"

# Minimal versions of the dev.ps1 console helpers the loaded functions call.
function Write-Err    { param([string]$m) Write-Host "  [ERR] $m" }
function Write-Status { param([string]$m) Write-Host "  [..] $m" }
function Write-Warn   { param([string]$m) Write-Host "  [WARN] $m" }
function Write-Ok     { param([string]$m) Write-Host "  [OK] $m" }

$script:passed = 0
$script:total = 0
function Report {
    param([string]$Name, [bool]$Ok, [string]$Detail)
    $script:total++
    if ($Ok) { $script:passed++; Write-Host "PASS  $Name" }
    else { Write-Host "FAIL  $Name  $Detail" }
}

# Parse dev.ps1 and return the source text of the named function ($null if absent).
# The caller dot-sources it at script level so the function lives in script scope.
$tokens = $null
$parseErrors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile($devPs1, [ref]$tokens, [ref]$parseErrors)
function Import-DevFunction {
    param([string]$Name)
    $found = $ast.FindAll({
        param($node)
        ($node -is [System.Management.Automation.Language.FunctionDefinitionAst]) -and ($node.Name -eq $Name)
    }, $true)
    if ($found.Count -eq 0) { return $null }
    return $found[0].Extent.Text
}
$reasonSrc  = Import-DevFunction "Get-FrontendInstallReason"
$installSrc = Import-DevFunction "Install-FrontendDependencies"
$npmPathSrc = Import-DevFunction "Get-NpmApplicationPath"
$hasReason  = ($null -ne $reasonSrc)
$hasInstall = ($null -ne $installSrc)
$hasNpmPath = ($null -ne $npmPathSrc)
if ($hasReason)  { . ([scriptblock]::Create($reasonSrc)) }
if ($hasNpmPath) { . ([scriptblock]::Create($npmPathSrc)) }
if ($hasInstall) { . ([scriptblock]::Create($installSrc)) }

# ---- helpers to build trees ----
function New-Tree {
    param([string]$Root, [bool]$Vite, [bool]$Lock)
    New-Item -ItemType Directory -Path $Root -Force | Out-Null
    $mods = Join-Path $Root "node_modules"
    New-Item -ItemType Directory -Path $mods -Force | Out-Null
    if ($Vite) {
        New-Item -ItemType Directory -Path (Join-Path $mods ".bin") -Force | Out-Null
        New-Item -ItemType Directory -Path (Join-Path $mods "vite\bin") -Force | Out-Null
        Set-Content -Path (Join-Path $mods ".bin\vite.cmd") -Value "rem" -Encoding ASCII
        Set-Content -Path (Join-Path $mods "vite\bin\vite.js") -Value "//" -Encoding ASCII
    }
    if ($Lock) {
        Set-Content -Path (Join-Path $Root "package-lock.json") -Value '{"lockfileVersion":3}' -Encoding ASCII
    }
}
function Get-LockHash { param([string]$Root) (Get-FileHash -Path (Join-Path $Root "package-lock.json") -Algorithm SHA256).Hash }
function Set-Marker { param([string]$Root, [string]$Value) Set-Content -Path (Join-Path $Root "node_modules\.asclexis-lockfile.sha256") -Value $Value -Encoding ASCII }

# ---- -Live mode: real npm, no stub, no server ----
if ($Live -ne "") {
    if (-not ($hasReason -and $hasInstall)) {
        Write-Host "FAIL  functions not found in dev.ps1"
        exit 1
    }
    $reason = Get-FrontendInstallReason -FrontendDir $Live
    Write-Host "reason: [$reason]"
    $ok = $true
    if ($reason -ne "") {
        $ok = [bool](Install-FrontendDependencies -FrontendDir $Live)
        Write-Host "install result: $ok"
    } else {
        Write-Host "install result: skipped (tree is current)"
    }
    $markerPath = Join-Path $Live "node_modules\.asclexis-lockfile.sha256"
    if (Test-Path $markerPath) { Write-Host "marker: $((Get-Content -Path $markerPath -TotalCount 1))" }
    else { Write-Host "marker: (absent)" }
    $after = Get-FrontendInstallReason -FrontendDir $Live
    Write-Host "reason after: [$after]"
    if ($ok -and $after -eq "") { exit 0 }
    exit 1
}

# ---- stub npm: real .cmd files (real child process, real exit code), one per behaviour ----
function New-NpmStub {
    param([string]$Path, [int]$Code, [bool]$CreateVite)
    $lines = @("@echo off", "echo %* > ""%~dp0args.txt""")
    if ($CreateVite) {
        $lines += "mkdir node_modules\.bin 2>nul"
        $lines += "mkdir node_modules\vite\bin 2>nul"
        $lines += "echo rem> node_modules\.bin\vite.cmd"
        $lines += "echo //> node_modules\vite\bin\vite.js"
    }
    $lines += "exit /b $Code"
    Set-Content -Path $Path -Value $lines -Encoding ASCII
}

$base = Join-Path ([System.IO.Path]::GetTempPath()) ("asclexis-check-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $base -Force | Out-Null
$stubDir = Join-Path $base "stubs"
New-Item -ItemType Directory -Path $stubDir -Force | Out-Null
$stubFail = Join-Path $stubDir "npm-fail.cmd";  New-NpmStub $stubFail 1 $false
$stubOk   = Join-Path $stubDir "npm-ok.cmd";    New-NpmStub $stubOk 0 $true
$stubNone = Join-Path $stubDir "npm-none.cmd";  New-NpmStub $stubNone 0 $false

try {
    if (-not $hasReason) { Report "Get-FrontendInstallReason is defined in dev.ps1" $false "function Get-FrontendInstallReason not found in dev.ps1" }
    if (-not $hasInstall) { Report "Install-FrontendDependencies is defined in dev.ps1" $false "function Install-FrontendDependencies not found in dev.ps1" }

    if ($hasReason) {
        function Check-Reason {
            param([string]$Name, [string]$Root, [string]$Expected)
            try {
                $got = [string](Get-FrontendInstallReason -FrontendDir $Root)
                Report $Name ($got -eq $Expected) "expected [$Expected] got [$got]"
            } catch {
                Report $Name $false "threw: $($_.Exception.Message)"
            }
        }

        $r1 = Join-Path $base "c1"; New-Item -ItemType Directory -Path $r1 -Force | Out-Null
        Check-Reason "1 no node_modules -> missing" $r1 "missing"

        $r2 = Join-Path $base "c2"; New-Tree $r2 $false $true
        Check-Reason "2 no vite -> incomplete" $r2 "incomplete"

        $r3 = Join-Path $base "c3"; New-Tree $r3 $true $true
        Check-Reason "3 marker missing -> lockfile-changed" $r3 "lockfile-changed"

        $r4 = Join-Path $base "c4"; New-Tree $r4 $true $true; Set-Marker $r4 (Get-LockHash $r4)
        Check-Reason "4 marker matches -> skip" $r4 ""

        $r5 = Join-Path $base "c5"; New-Tree $r5 $true $true; Set-Marker $r5 (Get-LockHash $r5)
        Add-Content -Path (Join-Path $r5 "package-lock.json") -Value "x" -Encoding ASCII
        Check-Reason "5 lockfile edited -> lockfile-changed" $r5 "lockfile-changed"

        $r6 = Join-Path $base "c6"; New-Tree $r6 $true $true; Set-Marker $r6 (Get-LockHash $r6)
        $lockItem = Get-Item (Join-Path $r6 "package-lock.json")
        $lockItem.LastWriteTime = (Get-Date).AddDays(-1)
        $back = [string](Get-FrontendInstallReason -FrontendDir $r6)
        $lockItem.LastWriteTime = (Get-Date).AddDays(1)
        $fwd = [string](Get-FrontendInstallReason -FrontendDir $r6)
        Report "6 mtime one day back and forward, content same -> skip both" (($back -eq "") -and ($fwd -eq "")) "back=[$back] forward=[$fwd]"

        $r7 = Join-Path $base "c7"; New-Tree $r7 $true $true; Set-Marker $r7 (Get-LockHash $r7)
        Remove-Item (Join-Path $r7 "package-lock.json") -Force
        Check-Reason "7 lockfile deleted -> lockfile-changed" $r7 "lockfile-changed"
    }

    if (-not $hasNpmPath) {
        Report "13 Get-NpmApplicationPath -> existing .cmd/.exe" $false "function Get-NpmApplicationPath not found in dev.ps1"
        Report "14 npm application --version -> exit 0, version number" $false "function Get-NpmApplicationPath not found in dev.ps1"
    }

    if ($hasInstall) {
        $markerName = "node_modules\.asclexis-lockfile.sha256"
        $argsFile = Join-Path $stubDir "args.txt"
        # `$NpmCommand` is a parameter of the shipped function; an older dev.ps1 lacks it and each call throws -> FAIL.

        $r8 = Join-Path $base "c8"; New-Tree $r8 $true $true
        try {
            $res8 = [bool](Install-FrontendDependencies -FrontendDir $r8 -NpmCommand $stubFail 6>$null)
            $noMarker8 = -not (Test-Path (Join-Path $r8 $markerName))
            Report "8 npm ci fails, old vite present -> false, no marker" ((-not $res8) -and $noMarker8) "result=$res8 markerAbsent=$noMarker8"
        } catch { Report "8 npm ci fails, old vite present -> false, no marker" $false "threw: $($_.Exception.Message)" }

        $r9 = Join-Path $base "c9"; New-Tree $r9 $false $true
        try {
            $res9 = [bool](Install-FrontendDependencies -FrontendDir $r9 -NpmCommand $stubOk 6>$null)
            $mp = Join-Path $r9 $markerName
            $markerOk = $false
            if (Test-Path $mp) { $markerOk = (([string](Get-Content -Path $mp -TotalCount 1)).Trim() -eq (Get-LockHash $r9)) }
            $after9 = ""
            if ($hasReason) { $after9 = [string](Get-FrontendInstallReason -FrontendDir $r9) }
            Report "9 npm ci ok, vite created -> true, marker = hash, then skip" ($res9 -and $markerOk -and ($after9 -eq "")) "result=$res9 markerOk=$markerOk reasonAfter=[$after9]"
        } catch { Report "9 npm ci ok, vite created -> true, marker = hash, then skip" $false "threw: $($_.Exception.Message)" }

        $r10 = Join-Path $base "c10"; New-Tree $r10 $false $true
        try {
            $res10 = [bool](Install-FrontendDependencies -FrontendDir $r10 -NpmCommand $stubNone 6>$null)
            $noMarker10 = -not (Test-Path (Join-Path $r10 $markerName))
            Report "10 npm ci ok, no vite -> false, no marker" ((-not $res10) -and $noMarker10) "result=$res10 markerAbsent=$noMarker10"
        } catch { Report "10 npm ci ok, no vite -> false, no marker" $false "threw: $($_.Exception.Message)" }

        $r11 = Join-Path $base "c11"; New-Tree $r11 $true $true
        $missingNpm = Join-Path $stubDir "does-not-exist.cmd"
        cmd /c exit 0
        try {
            $res11 = [bool](Install-FrontendDependencies -FrontendDir $r11 -NpmCommand $missingNpm 6>$null)
            $noMarker11 = -not (Test-Path (Join-Path $r11 $markerName))
            Report "11 npm cannot start, stale exit 0 -> false, no marker" ((-not $res11) -and $noMarker11) "result=$res11 markerAbsent=$noMarker11"
        } catch { Report "11 npm cannot start, stale exit 0 -> false, no marker" $false "threw: $($_.Exception.Message)" }

        $r12 = Join-Path $base "c12"; New-Tree $r12 $false $true
        if (Test-Path $argsFile) { Remove-Item $argsFile -Force }
        try {
            [void](Install-FrontendDependencies -FrontendDir $r12 -NpmCommand $stubOk 6>$null)
            $got12 = ""
            if (Test-Path $argsFile) { $got12 = ([string](Get-Content -Path $argsFile -TotalCount 1)).Trim() }
            Report "12 npm receives exactly: ci" ($got12 -eq "ci") "got [$got12]"
        } catch { Report "12 npm receives exactly: ci" $false "threw: $($_.Exception.Message)" }
    }

    if ($hasNpmPath) {
        $npmPath = [string](Get-NpmApplicationPath)
        $ext = ""
        if ($npmPath -ne "") { $ext = [System.IO.Path]::GetExtension($npmPath).ToLower() }
        $exists13 = ($npmPath -ne "") -and (Test-Path $npmPath)
        Report "13 Get-NpmApplicationPath -> existing .cmd/.exe" ($exists13 -and (($ext -eq ".cmd") -or ($ext -eq ".exe"))) "path=[$npmPath]"

        if ($exists13) {
            $ver = ""
            $code14 = -1
            try {
                $out14 = & $npmPath --version 2>&1
                $code14 = $LASTEXITCODE
                $ver = [string]($out14 | Select-Object -First 1)
            } catch { $ver = $_.Exception.Message }
            Report "14 npm application --version -> exit 0, version number" (($code14 -eq 0) -and ($ver -match '^\d+\.\d+\.\d+')) "exit=$code14 output=[$ver]"
        } else {
            Report "14 npm application --version -> exit 0, version number" $false "no npm application path"
        }
    }
}
finally {
    Set-Location ([System.IO.Path]::GetTempPath())
    Remove-Item -Path $base -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host "checks: $($script:passed)/$($script:total)"
if ($script:total -gt 0 -and $script:passed -eq $script:total -and $hasReason -and $hasInstall -and $hasNpmPath) { exit 0 }
exit 1
