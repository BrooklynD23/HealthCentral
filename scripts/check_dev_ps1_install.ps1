# Check script for the frontend install decision in dev.ps1 (STEP 5).
# Loads Get-FrontendInstallReason, Get-NpmApplicationPath and Install-FrontendDependencies
# out of dev.ps1 with the PowerShell parser, so the shipped code is tested and dev.ps1
# never runs. Windows PowerShell 5.1 compatible. Temp files live under the system temp
# folder only; nothing is written inside the repository.
#
#   check_dev_ps1_install.ps1                 run the 20 cases (npm is a stub npm.cmd on PATH)
#   check_dev_ps1_install.ps1 -Live <dir>     real decision + real `npm ci` against <dir>
param([string]$Live = "")

# The launcher's own setting (dev.ps1:19), so the functions behave as in production.
$ErrorActionPreference = "Continue"
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

# ---- helpers to build trees (LiteralPath everywhere: folder names may contain [ ]) ----
function New-Dir { param([string]$Path) [void][System.IO.Directory]::CreateDirectory($Path) }
function New-Tree {
    param([string]$Root, [bool]$Vite, [bool]$Lock)
    $mods = Join-Path $Root "node_modules"
    New-Dir $mods
    if ($Vite) {
        New-Dir (Join-Path $mods ".bin")
        New-Dir (Join-Path $mods "vite\bin")
        Set-Content -LiteralPath (Join-Path $mods ".bin\vite.cmd") -Value "rem" -Encoding ASCII
        Set-Content -LiteralPath (Join-Path $mods "vite\bin\vite.js") -Value "//" -Encoding ASCII
    }
    if ($Lock) {
        Set-Content -LiteralPath (Join-Path $Root "package-lock.json") -Value '{"lockfileVersion":3}' -Encoding ASCII
    }
}
function Get-LockHash { param([string]$Root) (Get-FileHash -LiteralPath (Join-Path $Root "package-lock.json") -Algorithm SHA256).Hash }
function Get-MarkerPath { param([string]$Root) Join-Path $Root "node_modules\.asclexis-lockfile.sha256" }
function Set-Marker { param([string]$Root, [string]$Value) Set-Content -LiteralPath (Get-MarkerPath $Root) -Value $Value -Encoding ASCII }
function Read-Marker {
    param([string]$Root)
    $mp = Get-MarkerPath $Root
    if (Test-Path -LiteralPath $mp) { return "$(Get-Content -LiteralPath $mp -TotalCount 1)".Trim() }
    return $null
}

# ---- -Live mode: real npm, no stub, no server ----
if ($Live -ne "") {
    if (-not ($hasReason -and $hasInstall -and $hasNpmPath)) {
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
    $recorded = Read-Marker $Live
    if ($null -ne $recorded) { Write-Host "marker: $recorded" } else { Write-Host "marker: (absent)" }
    $after = Get-FrontendInstallReason -FrontendDir $Live
    Write-Host "reason after: [$after]"
    if ($ok -and $after -eq "") { exit 0 }
    exit 1
}

# ---- stub npm: a file named npm.cmd in its own folder, a real child process ----
$base = Join-Path ([System.IO.Path]::GetTempPath()) ("asclexis-check-" + [guid]::NewGuid().ToString("N"))
New-Dir $base
function New-NpmStub {
    param([string]$Name, [int]$Code, [bool]$CreateVite, [bool]$Stderr, [string[]]$Extra = @())
    $dir = Join-Path $base $Name
    New-Dir $dir
    $lines = @("@echo off", "echo %* > ""%~dp0args.txt""")
    if ($Stderr) { $lines += "echo warn 1>&2" }
    if ($CreateVite) {
        $lines += "mkdir node_modules\.bin 2>nul"
        $lines += "mkdir node_modules\vite\bin 2>nul"
        $lines += "echo rem> node_modules\.bin\vite.cmd"
        $lines += "echo //> node_modules\vite\bin\vite.js"
    }
    $lines += $Extra
    $lines += "exit /b $Code"
    Set-Content -LiteralPath (Join-Path $dir "npm.cmd") -Value $lines -Encoding ASCII
    return $dir
}
function Read-StubArgs {
    param([string]$StubDir)
    $f = Join-Path $StubDir "args.txt"
    if (Test-Path -LiteralPath $f) { return "$(Get-Content -LiteralPath $f -TotalCount 1)".Trim() }
    return ""
}

# Runs a scriptblock with $env:PATH replaced; always restores it.
function Invoke-WithPath {
    param([string]$PathValue, [scriptblock]$Block)
    $saved = $env:PATH
    try {
        $env:PATH = $PathValue
        & $Block
    } finally {
        $env:PATH = $saved
    }
}

$script:junctions = @()
function Run-Case {
    param([string]$Name, [scriptblock]$Body)
    try { & $Body } catch { Report $Name $false "threw: $($_.Exception.Message)" }
}

try {
    if (-not $hasReason)  { Report "Get-FrontendInstallReason is defined in dev.ps1" $false "function Get-FrontendInstallReason not found in dev.ps1" }
    if (-not $hasInstall) { Report "Install-FrontendDependencies is defined in dev.ps1" $false "function Install-FrontendDependencies not found in dev.ps1" }
    if (-not $hasNpmPath) { Report "Get-NpmApplicationPath is defined in dev.ps1" $false "function Get-NpmApplicationPath not found in dev.ps1" }
    $realPath = $env:PATH

    # ---- decision cases 1-7 ----
    function Check-Reason {
        param([string]$Name, [string]$Root, [string]$Expected)
        Run-Case $Name {
            $got = [string](Get-FrontendInstallReason -FrontendDir $Root)
            Report $Name ($got -eq $Expected) "expected [$Expected] got [$got]"
        }
    }
    $r1 = Join-Path $base "c1"; New-Dir $r1
    Check-Reason "1 no node_modules -> missing" $r1 "missing"

    $r2 = Join-Path $base "c2"; New-Tree $r2 $false $true
    Check-Reason "2 no vite -> incomplete" $r2 "incomplete"

    $r3 = Join-Path $base "c3"; New-Tree $r3 $true $true
    Check-Reason "3 marker missing -> lockfile-changed" $r3 "lockfile-changed"

    $r4 = Join-Path $base "c4"; New-Tree $r4 $true $true; Set-Marker $r4 (Get-LockHash $r4)
    Check-Reason "4 marker matches -> skip" $r4 ""

    $r5 = Join-Path $base "c5"; New-Tree $r5 $true $true; Set-Marker $r5 (Get-LockHash $r5)
    Add-Content -LiteralPath (Join-Path $r5 "package-lock.json") -Value "x" -Encoding ASCII
    Check-Reason "5 lockfile edited -> lockfile-changed" $r5 "lockfile-changed"

    $r6 = Join-Path $base "c6"; New-Tree $r6 $true $true; Set-Marker $r6 (Get-LockHash $r6)
    Run-Case "6 mtime one day back and forward, content same -> skip both" {
        $lockItem = Get-Item -LiteralPath (Join-Path $r6 "package-lock.json")
        $lockItem.LastWriteTime = (Get-Date).AddDays(-1)
        $back = [string](Get-FrontendInstallReason -FrontendDir $r6)
        $lockItem.LastWriteTime = (Get-Date).AddDays(1)
        $fwd = [string](Get-FrontendInstallReason -FrontendDir $r6)
        Report "6 mtime one day back and forward, content same -> skip both" (($back -eq "") -and ($fwd -eq "")) "back=[$back] forward=[$fwd]"
    }

    $r7 = Join-Path $base "c7"; New-Tree $r7 $true $true; Set-Marker $r7 (Get-LockHash $r7)
    Remove-Item -LiteralPath (Join-Path $r7 "package-lock.json") -Force
    Check-Reason "7 lockfile deleted -> lockfile-changed" $r7 "lockfile-changed"

    # ---- install cases 8-15: Install-FrontendDependencies -FrontendDir only ----
    $stubFail   = New-NpmStub "stub-fail" 1 $false $false
    $stubOk     = New-NpmStub "stub-ok" 0 $true $false
    $stubNone   = New-NpmStub "stub-none" 0 $false $false
    $stubArgs   = New-NpmStub "stub-args" 0 $true $false
    $stubStderr = New-NpmStub "stub-stderr" 0 $true $true
    $stubBrack  = New-NpmStub "stub-brack" 0 $true $false
    $stubShim   = New-NpmStub "stub-shim" 0 $true $false

    $n = "8 npm ci fails, old vite + old marker -> false, marker gone"
    Run-Case $n {
        $r = Join-Path $base "c8"; New-Tree $r $true $true; Set-Marker $r (Get-LockHash $r)
        $res = $false
        Invoke-WithPath "$stubFail;$realPath" { $script:res8 = [bool](Install-FrontendDependencies -FrontendDir $r 6>$null) }
        $gone = ($null -eq (Read-Marker $r))
        Report $n ((-not $script:res8) -and $gone) "result=$($script:res8) markerGone=$gone"
    }

    $n = "9 npm ci ok, vite created -> true, marker = hash, then skip"
    Run-Case $n {
        $r = Join-Path $base "c9"; New-Tree $r $false $true
        Invoke-WithPath "$stubOk;$realPath" { $script:res9 = [bool](Install-FrontendDependencies -FrontendDir $r 6>$null) }
        $markerOk = ((Read-Marker $r) -eq (Get-LockHash $r))
        $after = [string](Get-FrontendInstallReason -FrontendDir $r)
        Report $n ($script:res9 -and $markerOk -and ($after -eq "")) "result=$($script:res9) markerOk=$markerOk reasonAfter=[$after]"
    }

    $n = "10 npm ci ok, no vite -> false, no marker"
    Run-Case $n {
        $r = Join-Path $base "c10"; New-Tree $r $false $true
        Invoke-WithPath "$stubNone;$realPath" { $script:res10 = [bool](Install-FrontendDependencies -FrontendDir $r 6>$null) }
        $gone = ($null -eq (Read-Marker $r))
        Report $n ((-not $script:res10) -and $gone) "result=$($script:res10) markerGone=$gone"
    }

    $n = "11 npm not on PATH, stale exit 0 -> false, no marker"
    Run-Case $n {
        $r = Join-Path $base "c11"; New-Tree $r $true $true
        Invoke-WithPath (Join-Path $env:SystemRoot "System32") {
            cmd /c exit 0
            $script:res11 = [bool](Install-FrontendDependencies -FrontendDir $r 6>$null)
        }
        $gone = ($null -eq (Read-Marker $r))
        Report $n ((-not $script:res11) -and $gone) "result=$($script:res11) markerGone=$gone"
    }

    $n = "12 npm receives exactly: ci"
    Run-Case $n {
        $r = Join-Path $base "c12"; New-Tree $r $false $true
        Invoke-WithPath "$stubArgs;$realPath" { [void](Install-FrontendDependencies -FrontendDir $r 6>$null) }
        $got = Read-StubArgs $stubArgs
        Report $n ($got -eq "ci") "got [$got]"
    }

    $n = "13 npm ci ok but writes to stderr -> true, marker written"
    Run-Case $n {
        $r = Join-Path $base "c13"; New-Tree $r $false $true
        Invoke-WithPath "$stubStderr;$realPath" { $script:res13 = [bool](Install-FrontendDependencies -FrontendDir $r 6>$null) }
        $markerOk = ((Read-Marker $r) -eq (Get-LockHash $r))
        Report $n ($script:res13 -and $markerOk) "result=$($script:res13) markerOk=$markerOk"
    }

    $n = "14 npm.cmd chosen over extensionless npm and npm.ps1 earlier on PATH"
    Run-Case $n {
        $shimDir = Join-Path $base "shim"; New-Dir $shimDir
        Set-Content -LiteralPath (Join-Path $shimDir "npm") -Value "not a program" -Encoding ASCII
        Set-Content -LiteralPath (Join-Path $shimDir "npm.ps1") -Value "Set-Content -LiteralPath '$shimDir\shim-was-called.txt' -Value x" -Encoding ASCII
        $r = Join-Path $base "c14"; New-Tree $r $false $true
        $script:found14 = ""
        Invoke-WithPath "$shimDir;$stubShim;$realPath" {
            $script:found14 = [string](Get-NpmApplicationPath)
            [void](Install-FrontendDependencies -FrontendDir $r 6>$null)
        }
        $want = Join-Path $stubShim "npm.cmd"
        $got = Read-StubArgs $stubShim
        $shimRan = Test-Path -LiteralPath (Join-Path $shimDir "shim-was-called.txt")
        Report $n (($script:found14 -ieq $want) -and ($got -eq "ci") -and (-not $shimRan)) "path=[$($script:found14)] args=[$got] shimRan=$shimRan"
    }

    $n = "15 folder name with space and brackets -> true, then skip"
    Run-Case $n {
        $r = Join-Path $base "Asclexis [1] test"; New-Dir $r
        Set-Content -LiteralPath (Join-Path $r "package-lock.json") -Value '{"lockfileVersion":3}' -Encoding ASCII
        Invoke-WithPath "$stubBrack;$realPath" { $script:res15 = [bool](Install-FrontendDependencies -FrontendDir $r 6>$null) }
        $after = [string](Get-FrontendInstallReason -FrontendDir $r)
        Report $n ($script:res15 -and ($after -eq "")) "result=$($script:res15) reasonAfter=[$after]"
    }

    # ---- 19: node_modules is a junction -> refuse, touch nothing ----
    $n = "19 node_modules is a junction -> false, target untouched, npm not run"
    Run-Case $n {
        $stubRan = New-NpmStub "stub-ran" 0 $true $false @('echo x> "%~dp0ran.txt"')
        $r = Join-Path $base "c19"; New-Dir $r
        Set-Content -LiteralPath (Join-Path $r "package-lock.json") -Value '{"lockfileVersion":3}' -Encoding ASCII
        $target = Join-Path $base "c19-target"; New-Tree $target $true $false
        Set-Content -LiteralPath (Join-Path $target "precious.txt") -Value "keep" -Encoding ASCII
        $link = Join-Path $r "node_modules"
        [void](Remove-Item -LiteralPath $link -Recurse -Force -ErrorAction SilentlyContinue)
        $script:junctions += $link
        [void](cmd /c mklink /J "$link" "$(Join-Path $target 'node_modules')" 2>&1)
        # the target's own node_modules holds the Vite files; the link must see them too
        $isLink = [bool]((Get-Item -LiteralPath $link -Force).Attributes -band [System.IO.FileAttributes]::ReparsePoint)
        Set-Content -LiteralPath (Join-Path (Join-Path $target "node_modules") "precious.txt") -Value "keep" -Encoding ASCII
        Invoke-WithPath "$stubRan;$realPath" { $script:res19 = [bool](Install-FrontendDependencies -FrontendDir $r 6>$null) }
        $keep = Test-Path -LiteralPath (Join-Path (Join-Path $target "node_modules") "precious.txt")
        $linkOk = Test-Path -LiteralPath $link
        $ran = Test-Path -LiteralPath (Join-Path $stubRan "ran.txt")
        $mk = Test-Path -LiteralPath (Join-Path (Join-Path $target "node_modules") ".asclexis-lockfile.sha256")
        Report $n ($isLink -and (-not $script:res19) -and $keep -and $linkOk -and (-not $ran) -and (-not $mk)) "isLink=$isLink result=$($script:res19) precious=$keep link=$linkOk npmRan=$ran markerInTarget=$mk"
    }

    # ---- 20: lockfile changes while npm runs ----
    $n = "20 lockfile changed mid-install -> true, marker = hash before npm, then lockfile-changed"
    Run-Case $n {
        $stubMid = New-NpmStub "stub-mid" 0 $true $false @('>>package-lock.json echo x')
        $r = Join-Path $base "c20"; New-Tree $r $false $true
        $before = Get-LockHash $r
        Invoke-WithPath "$stubMid;$realPath" { $script:res20 = [bool](Install-FrontendDependencies -FrontendDir $r 6>$null) }
        $rec = Read-Marker $r
        $after = [string](Get-FrontendInstallReason -FrontendDir $r)
        Report $n ($script:res20 -and ($rec -eq $before) -and ($after -eq "lockfile-changed")) "result=$($script:res20) markerIsBefore=$($rec -eq $before) reasonAfter=[$after]"
    }

    # ---- 16: empty marker ----
    $n = "16 empty marker -> lockfile-changed, no error record"
    Run-Case $n {
        $r = Join-Path $base "c16"; New-Tree $r $true $true
        [System.IO.File]::WriteAllBytes((Get-MarkerPath $r), (New-Object byte[] 0))
        $Error.Clear()
        $got = [string](Get-FrontendInstallReason -FrontendDir $r)
        $errs = $Error.Count
        Report $n (($got -eq "lockfile-changed") -and ($errs -eq 0)) "got [$got] errors=$errs"
    }

    # ---- 17-18: the real npm, no network, no install ----
    $npmPath = ""
    if ($hasNpmPath) { $npmPath = [string](Get-NpmApplicationPath) }
    $ext = ""
    if ($npmPath -ne "") { $ext = [System.IO.Path]::GetExtension($npmPath).ToLower() }
    $exists = ($npmPath -ne "") -and (Test-Path -LiteralPath $npmPath)
    Report "17 Get-NpmApplicationPath (real PATH) -> existing .cmd/.exe" ($exists -and (($ext -eq ".cmd") -or ($ext -eq ".exe"))) "path=[$npmPath]"

    $n = "18 npm application ci --help -> exit 0, mentions npm ci"
    if ($exists) {
        Run-Case $n {
            $out = & $npmPath ci --help 2>&1
            $code = $LASTEXITCODE
            $text = ($out | ForEach-Object { "$_" }) -join "`n"
            Report $n (($code -eq 0) -and ($text -match 'npm ci')) "exit=$code output=[$($text.Substring(0, [Math]::Min(80, $text.Length)))]"
        }
    } else {
        Report $n $false "no npm application path"
    }
}
finally {
    Set-Location ([System.IO.Path]::GetTempPath())
    # rmdir without /s removes only the link, never the target; must precede the recursive delete.
    foreach ($j in $script:junctions) { if (Test-Path -LiteralPath $j) { cmd /c rmdir "$j" | Out-Null } }
    Remove-Item -LiteralPath $base -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host "checks: $($script:passed)/$($script:total)"
if ($script:total -eq 20 -and $script:passed -eq 20 -and $hasReason -and $hasInstall -and $hasNpmPath) { exit 0 }
exit 1
