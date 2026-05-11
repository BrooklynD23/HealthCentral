# Dynamic Port Selection for dev.ps1

**Date:** 2026-05-11
**Status:** Approved

## Problem

`dev.ps1` hardcodes `$FRONTEND_PORT = 3000` and `$BACKEND_PORT = 8000`. If either port is in use and can't be freed (UAC denied, system-reserved range, stubborn service), the script exits with an error instead of recovering. The browser is also always opened at `http://localhost:3000` regardless of what port Vite actually uses.

## Goal

When a default port is unavailable and can't be freed, the script automatically finds the next free port (sequentially from default+1) and uses it — for both servers. The frontend is always wired to the correct backend port.

## Approach: Pre-scan and resolve ports before launch

### 1. New `Find-FreePort` helper

Added alongside the existing port helpers in `dev.ps1`:

```powershell
function Find-FreePort {
    param([int]$StartPort, [int]$MaxPort = 65535)
    for ($port = $StartPort; $port -le $MaxPort; $port++) {
        if (-not (Test-PortInUse $port)) { return $port }
    }
    throw "No free port found between $StartPort and $MaxPort"
}
```

### 2. Step 7 — best-effort kill, then resolve

The existing kill attempt (`Stop-ProcessOnPort`) is retained as a clean-shutdown step, but failure no longer causes `exit 1`. After the (optional) kill attempt, `Find-FreePort` runs from the default port to return a guaranteed-free port:

```powershell
# Best-effort kill (non-fatal)
if (Test-PortInUse $BACKEND_PORT) {
    Write-Warn "Port $BACKEND_PORT in use. Trying to free it ..."
    Stop-ProcessOnPort $BACKEND_PORT
    Start-Sleep -Seconds 1
}
$resolvedBackendPort = Find-FreePort -StartPort $BACKEND_PORT
if ($resolvedBackendPort -ne $BACKEND_PORT) {
    Write-Warn "Port $BACKEND_PORT unavailable — using port $resolvedBackendPort for backend"
} else {
    Write-Ok "Port $resolvedBackendPort is available (backend)"
}

# Same pattern for frontend
if (Test-PortInUse $FRONTEND_PORT) {
    Write-Warn "Port $FRONTEND_PORT in use. Trying to free it ..."
    Stop-ProcessOnPort $FRONTEND_PORT
    Start-Sleep -Seconds 1
}
$resolvedFrontendPort = Find-FreePort -StartPort $FRONTEND_PORT
if ($resolvedFrontendPort -ne $FRONTEND_PORT) {
    Write-Warn "Port $FRONTEND_PORT unavailable — using port $resolvedFrontendPort for frontend"
} else {
    Write-Ok "Port $resolvedFrontendPort is available (frontend)"
}
```

### 3. `src/frontend/.env.local` sync

Before launching servers, write the resolved backend port:

```powershell
$frontendEnvLocal = Join-Path $FRONTEND_DIR ".env.local"
Set-DotEnvKey -FilePath $frontendEnvLocal -Key "VITE_API_URL" `
    -Value "http://localhost:$resolvedBackendPort/api/v1"
```

Vite loads `.env.local` automatically and it takes priority over `.env`. The existing `VITE_API_URL` fallback in `api.ts` (`http://localhost:8000/api/v1`) remains as a safety net for non-script launches. `.env.local` is already gitignored by Vite convention.

### 4. Server launch updates (Step 8)

- **Backend**: `--port $resolvedBackendPort`
- **Frontend**: `--port $resolvedFrontendPort --strictPort` (forces Vite to use exactly the pre-verified port)
- **Banner**: display resolved ports, not defaults
- **Browser open** (Step 9): `http://localhost:$resolvedFrontendPort`
- **Restart logic** (Step 10): use resolved ports for both server restarts

### 5. `dev.bat`

No changes required — it is a pass-through wrapper to `dev.ps1`.

## Files Changed

| File | Change |
|------|--------|
| `dev.ps1` | Add `Find-FreePort`; rework Step 7; add `.env.local` write; update Steps 8, 9, 10 |
| `src/frontend/.env.local` | Created/updated at runtime by the script (not committed) |

## Out of Scope

- Linux/Mac shell equivalents (`dev.sh`) — not part of this project
- Changes to `vite.config.ts` — `strictPort: false` stays as-is; CLI `--strictPort` overrides it at launch time
