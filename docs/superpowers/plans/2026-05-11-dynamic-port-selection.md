# Dynamic Port Selection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `dev.ps1` automatically find the next free port when the default backend (8000) or frontend (3000) port is unavailable, rather than aborting, and keep the frontend wired to the correct backend URL at all times.

**Architecture:** Add a `Find-FreePort` helper that scans sequentially from a start port. Step 7 becomes best-effort (kill attempt no longer fatal) and resolves both ports into `$resolvedBackendPort` / `$resolvedFrontendPort`. The resolved backend port is written to `src/frontend/.env.local` as `VITE_API_URL` before Vite starts. All downstream references to the hardcoded port variables are swapped for the resolved variables.

**Tech Stack:** PowerShell 5+, Vite `.env.local` convention (auto-loaded, highest precedence)

---

## File Map

| File | Change |
|------|--------|
| `dev.ps1` | Add `Find-FreePort` (after line 177); replace Step 7 (lines 563–598); add Step 7b `.env.local` write; update Steps 8, 9, 10 port references |
| `src/frontend/.env.local` | Created/updated at script runtime — not committed |

---

### Task 1: Add `Find-FreePort` helper

**Files:**
- Modify: `dev.ps1` — insert after line 177 (closing `}` of `Stop-ProcessOnPort`)

- [ ] **Step 1: Open a PowerShell console and verify the test harness works**

Run this snippet standalone to confirm the TCP-listener trick works on this machine:

```powershell
$l = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 19999)
$l.Start()
$conn = Get-NetTCPConnection -LocalPort 19999 -State Listen -ErrorAction SilentlyContinue
Write-Host "Port blocked: $($null -ne $conn)"   # should print True
$l.Stop()
```

Expected output: `Port blocked: True`

- [ ] **Step 2: Write the failing test**

In a fresh PowerShell console run:

```powershell
# Inline test — no external file needed
function Test-PortInUse {
    param([int]$Port)
    $null -ne (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
}
function Find-FreePort {
    # NOT IMPLEMENTED YET — should throw
    throw "not implemented"
}
$l = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 19999)
$l.Start()
try {
    $result = Find-FreePort -StartPort 19999
    Write-Host "FAIL: expected throw, got $result" -ForegroundColor Red
} catch {
    Write-Host "PASS (expected): Find-FreePort threw because not implemented" -ForegroundColor Green
} finally { $l.Stop() }
```

Expected: `PASS (expected): Find-FreePort threw because not implemented`

- [ ] **Step 3: Add `Find-FreePort` to `dev.ps1` after line 177**

Insert the following block between the closing `}` of `Stop-ProcessOnPort` (line 177) and the blank line before `Refresh-EnvPathFromRegistry` (line 179):

```powershell
function Find-FreePort {
    param([int]$StartPort, [int]$MaxPort = 65535)
    for ($port = $StartPort; $port -le $MaxPort; $port++) {
        if (-not (Test-PortInUse $port)) { return $port }
    }
    throw "No free port found between $StartPort and $MaxPort"
}
```

- [ ] **Step 4: Run the test again — now it should pass**

Same console, redefine `Find-FreePort` with the real body:

```powershell
function Test-PortInUse {
    param([int]$Port)
    $null -ne (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
}
function Find-FreePort {
    param([int]$StartPort, [int]$MaxPort = 65535)
    for ($port = $StartPort; $port -le $MaxPort; $port++) {
        if (-not (Test-PortInUse $port)) { return $port }
    }
    throw "No free port found between $StartPort and $MaxPort"
}

# Test 1: port is free — should return StartPort unchanged
$free = Find-FreePort -StartPort 19998
if ($free -eq 19998) { Write-Host "PASS: returns start port when free" -ForegroundColor Green }
else { Write-Host "FAIL: expected 19998, got $free" -ForegroundColor Red }

# Test 2: port is blocked — should return StartPort+1
$l = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 19999)
$l.Start()
try {
    $found = Find-FreePort -StartPort 19999
    if ($found -eq 20000) { Write-Host "PASS: returns next free port" -ForegroundColor Green }
    else { Write-Host "FAIL: expected 20000, got $found" -ForegroundColor Red }
} finally { $l.Stop() }
```

Expected:
```
PASS: returns start port when free
PASS: returns next free port
```

- [ ] **Step 5: Commit**

```bash
git add dev.ps1
git commit -m "feat: add Find-FreePort helper to dev.ps1"
```

---

### Task 2: Rework Step 7 — best-effort kill, then resolve ports

**Files:**
- Modify: `dev.ps1` lines 563–598 (Step 7 block, including trailing blank line at 598)

- [ ] **Step 1: Replace Step 7 entirely**

Delete lines 563–598 and replace with:

```powershell
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
    Write-Warn "Port $BACKEND_PORT still in use — using port $resolvedBackendPort for backend"
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
    Write-Warn "Port $FRONTEND_PORT still in use — using port $resolvedFrontendPort for frontend"
} else {
    Write-Ok "Port $resolvedFrontendPort is available (frontend)"
}

Write-Host ""
```

- [ ] **Step 2: Smoke-test the new Step 7 in isolation**

Block port 3000 in one console, then run `dev.ps1` up to the point where it would print the port status (Ctrl+C after the port lines appear). You should see:

```
  [!] Port 3000 is in use. Trying to free it ...
  [!] Port 3000 still in use — using port 3001 for frontend
  [+] Port 8000 is available (backend)
```

(If 8000 is also blocked, repeat for backend.)

- [ ] **Step 3: Commit**

```bash
git add dev.ps1
git commit -m "feat: rework Step 7 to find free ports instead of aborting"
```

---

### Task 3: Sync `src/frontend/.env.local` with resolved backend port

**Files:**
- Modify: `dev.ps1` — insert new Step 7b between the end of Step 7 and the blank line before Step 8

- [ ] **Step 1: Add the `.env.local` write block**

Insert after the `Write-Host ""` that closes Step 7 (the blank line at the end of the new Step 7 block added in Task 2), and before the Step 8 header comment:

```powershell
# ===================================================================
#  STEP 7b - Sync frontend .env.local with resolved backend port
# ===================================================================
$frontendEnvLocal = Join-Path $FRONTEND_DIR ".env.local"
Set-DotEnvKey -FilePath $frontendEnvLocal -Key "VITE_API_URL" `
    -Value "http://localhost:$resolvedBackendPort/api/v1"
Write-Ok "Synced .env.local: VITE_API_URL=http://localhost:$resolvedBackendPort/api/v1"
Write-Host ""
```

- [ ] **Step 2: Verify `.env.local` is gitignored**

Run:

```bash
echo "src/frontend/.env.local" | git check-ignore --stdin
```

Expected output: `src/frontend/.env.local`

If it is NOT ignored, add it:

```bash
echo ".env.local" >> src/frontend/.gitignore
git add src/frontend/.gitignore
```

- [ ] **Step 3: Test `.env.local` write manually**

In PowerShell, run the snippet in isolation (replace `$FRONTEND_DIR` and `$resolvedBackendPort` with real values):

```powershell
function Set-DotEnvKey {
    param([string]$FilePath, [string]$Key, [string]$Value)
    $pattern = "^\s*$([regex]::Escape($Key))\s*="
    $newLine = "$Key=$Value"
    $lines = if (Test-Path -LiteralPath $FilePath) { Get-Content -LiteralPath $FilePath } else { @() }
    $out = New-Object System.Collections.Generic.List[string]
    $found = $false
    foreach ($line in $lines) {
        if ($line -match $pattern) {
            if (-not $found) { [void]$out.Add($newLine); $found = $true }
        } else { [void]$out.Add($line) }
    }
    if (-not $found) {
        if ($out.Count -gt 0 -and $out[$out.Count - 1] -ne '') { [void]$out.Add('') }
        [void]$out.Add($newLine)
    }
    $out | Set-Content -LiteralPath $FilePath
}

$testFile = "$env:TEMP\test-env-local.txt"
Set-DotEnvKey -FilePath $testFile -Key "VITE_API_URL" -Value "http://localhost:8001/api/v1"
$content = Get-Content $testFile -Raw
if ($content -match "VITE_API_URL=http://localhost:8001/api/v1") {
    Write-Host "PASS: .env.local written correctly" -ForegroundColor Green
} else {
    Write-Host "FAIL: got: $content" -ForegroundColor Red
}
# Second call — should update, not duplicate
Set-DotEnvKey -FilePath $testFile -Key "VITE_API_URL" -Value "http://localhost:8002/api/v1"
$lines = Get-Content $testFile
$matches = $lines | Where-Object { $_ -match "VITE_API_URL=" }
if ($matches.Count -eq 1 -and $matches[0] -eq "VITE_API_URL=http://localhost:8002/api/v1") {
    Write-Host "PASS: update replaces, does not duplicate" -ForegroundColor Green
} else {
    Write-Host "FAIL: duplicate or wrong value: $($matches -join '; ')" -ForegroundColor Red
}
Remove-Item $testFile -Force
```

Expected:
```
PASS: .env.local written correctly
PASS: update replaces, does not duplicate
```

- [ ] **Step 4: Commit**

```bash
git add dev.ps1
git commit -m "feat: write VITE_API_URL to .env.local before Vite launch"
```

---

### Task 4: Update Steps 8, 9, 10 to use resolved ports

**Files:**
- Modify: `dev.ps1` lines 607–609 (Step 8 banner), 618 (backend launch), 630 (frontend launch args), 655/660/669 (Step 9 URLs), 714 (Step 10 backend restart), 724–728 (Step 10 frontend restart)

> **Note:** Line numbers reference the file *before* Tasks 1–3 edits. After those edits, line numbers shift slightly. Use the surrounding text as anchor rather than exact line numbers.

- [ ] **Step 1: Update Step 8 banner (find the three `Write-Host` lines showing the URLs)**

Replace:
```powershell
Write-Host "    Backend API:  http://localhost:$BACKEND_PORT" -ForegroundColor Cyan
Write-Host "    Frontend:     http://localhost:$FRONTEND_PORT" -ForegroundColor Cyan
Write-Host "    API Docs:     http://localhost:$BACKEND_PORT/docs" -ForegroundColor Cyan
```

With:
```powershell
Write-Host "    Backend API:  http://localhost:$resolvedBackendPort" -ForegroundColor Cyan
Write-Host "    Frontend:     http://localhost:$resolvedFrontendPort" -ForegroundColor Cyan
Write-Host "    API Docs:     http://localhost:$resolvedBackendPort/docs" -ForegroundColor Cyan
```

- [ ] **Step 2: Update backend launch args**

Replace:
```powershell
$backendProc = Start-Process -FilePath $venvPython `
    -ArgumentList "-m", "uvicorn", "main:app", "--reload", "--host", "127.0.0.1", "--port", "$BACKEND_PORT" `
    -WorkingDirectory $BACKEND_DIR `
    -WindowStyle Hidden `
    -PassThru
```

With:
```powershell
$backendProc = Start-Process -FilePath $venvPython `
    -ArgumentList "-m", "uvicorn", "main:app", "--reload", "--host", "127.0.0.1", "--port", "$resolvedBackendPort" `
    -WorkingDirectory $BACKEND_DIR `
    -WindowStyle Hidden `
    -PassThru
```

- [ ] **Step 3: Update frontend (Vite) launch args**

Replace:
```powershell
$frontendProc = Start-Process -FilePath $frontendVite `
    -ArgumentList "--port", "$FRONTEND_PORT" `
    -WorkingDirectory $FRONTEND_DIR `
    -WindowStyle Hidden `
    -PassThru
```

With:
```powershell
$frontendProc = Start-Process -FilePath $frontendVite `
    -ArgumentList "--port", "$resolvedFrontendPort", "--strictPort" `
    -WorkingDirectory $FRONTEND_DIR `
    -WindowStyle Hidden `
    -PassThru
```

- [ ] **Step 4: Update Step 9 browser-open URLs**

Replace both occurrences of `"http://localhost:$FRONTEND_PORT"` in Step 9 (the `Invoke-WebRequest` URI and both `Start-Process` calls):

```powershell
# In the while loop:
$response = Invoke-WebRequest -Uri "http://localhost:$resolvedFrontendPort" `
                -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue
# ...
            Start-Process "http://localhost:$resolvedFrontendPort"

# Fallback:
    Start-Process "http://localhost:$resolvedFrontendPort"
```

- [ ] **Step 5: Update Step 10 backend restart args**

Replace:
```powershell
$backendProc = Start-Process -FilePath $venvPython `
    -ArgumentList "-m", "uvicorn", "main:app", "--reload", "--host", "127.0.0.1", "--port", "$BACKEND_PORT" `
    -WorkingDirectory $BACKEND_DIR `
    -WindowStyle Hidden `
    -PassThru
```
(inside the `if ($backendDead)` block)

With:
```powershell
$backendProc = Start-Process -FilePath $venvPython `
    -ArgumentList "-m", "uvicorn", "main:app", "--reload", "--host", "127.0.0.1", "--port", "$resolvedBackendPort" `
    -WorkingDirectory $BACKEND_DIR `
    -WindowStyle Hidden `
    -PassThru
```

- [ ] **Step 6: Update Step 10 frontend restart args**

Replace:
```powershell
$frontendProc = Start-Process -FilePath $frontendVite `
    -ArgumentList "--port", "$FRONTEND_PORT" `
    -WorkingDirectory $FRONTEND_DIR `
    -WindowStyle Hidden `
    -PassThru
```
(inside the `if ($frontendDead)` block)

With:
```powershell
$frontendProc = Start-Process -FilePath $frontendVite `
    -ArgumentList "--port", "$resolvedFrontendPort", "--strictPort" `
    -WorkingDirectory $FRONTEND_DIR `
    -WindowStyle Hidden `
    -PassThru
```

- [ ] **Step 7: Grep for any remaining raw `$BACKEND_PORT` / `$FRONTEND_PORT` usages in Steps 7–10**

Run:
```powershell
Select-String -Path dev.ps1 -Pattern '\$BACKEND_PORT|\$FRONTEND_PORT' |
    Where-Object { $_.LineNumber -ge 562 }
```

Expected: only the two variable declarations at the top of the file (`$BACKEND_PORT = 8000`, `$FRONTEND_PORT = 3000`). If any others appear at line 562+, replace them with the resolved equivalents.

- [ ] **Step 8: Full smoke test**

Block port 3000 with a TCP listener in a separate console:
```powershell
$l = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 3000)
$l.Start()
Read-Host "Press Enter to release"
```

Then run `.\dev.bat` in a second console. Verify:
1. Script prints `Port 3000 still in use — using port 3001 for frontend`
2. Script prints `Synced .env.local: VITE_API_URL=http://localhost:8000/api/v1`
3. Browser opens at `http://localhost:3001`
4. `src/frontend/.env.local` contains `VITE_API_URL=http://localhost:8000/api/v1`
5. App loads and API calls succeed (login or health check endpoint responds)

- [ ] **Step 9: Commit**

```bash
git add dev.ps1
git commit -m "feat: use resolved ports throughout Steps 8-10 in dev.ps1"
```
