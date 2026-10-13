#!/usr/bin/env bash
# Asclexis development launcher for WSL/Linux (and macOS). Mirrors dev.ps1:
# prerequisite checks, backend venv + pip (SQLCipher fallback), .env, OCR_ENABLED
# sync, npm ci on lockfile change, free-port resolution, both servers on 127.0.0.1.
# Ctrl+C stops both servers.
#
# Clone into your Linux home (e.g. ~/HealthCentral), NOT under /mnt/c: the
# Windows mount is slow, file watching is unreliable, and Windows and Linux
# cannot share the venv or node_modules. Set HC_ALLOW_WINDOWS_MOUNT=1 to override.
# Set HC_SKIP_OCR_SETUP=1 to leave OCR_ENABLED in src/backend/.env untouched.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
BACKEND_DIR="$ROOT_DIR/src/backend"
FRONTEND_DIR="$ROOT_DIR/src/frontend"
VENV_DIR="$BACKEND_DIR/.venv-linux"   # dev.ps1 owns src/backend/venv (Windows)
ENV_FILE="$BACKEND_DIR/.env"
ENV_EXAMPLE="$ROOT_DIR/config/.env.example"
LOG_DIR="$ROOT_DIR/logs"
BACKEND_PORT=8000
FRONTEND_PORT=3000

status() { printf '  [*] %s\n' "$*"; }
ok()     { printf '  [+] %s\n' "$*"; }
warn()   { printf '  [!] %s\n' "$*" >&2; }
die()    { printf '  [-] %s\n' "$*" >&2; exit 1; }

# Same contract as dev.ps1 Set-DotEnvKey: replace the first KEY= line, drop
# duplicates, append (after a blank line) when absent.
set_env_key() {
  local file="$1" key="$2" value="$3" tmp
  touch "$file"
  tmp="$(mktemp)"
  awk -v k="$key" -v v="$value" '
    $0 ~ "^[[:space:]]*" k "[[:space:]]*=" { if (!done) print k "=" v; done = 1; next }
    { print; last = $0 }
    END { if (!done) { if (NR > 0 && last != "") print ""; print k "=" v } }
  ' "$file" > "$tmp"
  cat "$tmp" > "$file" && rm -f "$tmp"
}

port_busy() { (: <>"/dev/tcp/127.0.0.1/$1") 2>/dev/null; }
free_port() {
  local p="$1"
  while port_busy "$p"; do p=$((p + 1)); [ "$p" -le 65535 ] || die "No free port from $1"; done
  echo "$p"
}

lock_hash() { { sha256sum "$1" 2>/dev/null || shasum -a 256 "$1"; } | cut -d' ' -f1 | tr 'a-f' 'A-F'; }

echo ""
echo "  ============================================="
echo "    Asclexis  -  Development Server (dev.sh)"
echo "  ============================================="
echo ""

# --- Location check -------------------------------------------------------
case "$ROOT_DIR" in
  /mnt/[a-zA-Z]/*)
    warn "This checkout is on a Windows drive mount: $ROOT_DIR"
    warn "WSL on /mnt/* is slow, Vite/uvicorn file watching is unreliable, and"
    warn "Windows and Linux cannot share src/backend venvs or src/frontend/node_modules"
    warn "(npm ci here would replace the Windows node_modules with Linux binaries)."
    warn "Clone into your Linux home instead:"
    warn "  git clone <repo-url> ~/HealthCentral && cd ~/HealthCentral && ./dev.sh"
    [ "${HC_ALLOW_WINDOWS_MOUNT:-}" = "1" ] || die "Refusing to run. Set HC_ALLOW_WINDOWS_MOUNT=1 to override."
    warn "HC_ALLOW_WINDOWS_MOUNT=1 set; continuing anyway."
    ;;
esac

# --- STEP 1: prerequisites --------------------------------------------------
echo "  --- Checking prerequisites ---"
PYTHON=""
for cmd in python3.11 python3.12 python3.13 python3 python; do
  if command -v "$cmd" >/dev/null 2>&1 && "$cmd" -c 'import sys; sys.exit(sys.version_info < (3, 11))' 2>/dev/null; then
    PYTHON="$cmd"; break
  fi
done
[ -n "$PYTHON" ] || die "Python 3.11+ is required but not found. Install: sudo apt install python3.11 python3.11-venv  (macOS: brew install python@3.11)"
ok "Found $("$PYTHON" --version 2>&1) ($PYTHON)"

command -v node >/dev/null 2>&1 || die "Node.js 22.12+ is required but not found. Install via nvm: nvm install 24  (or https://nodejs.org)"
NODE_VERSION="$(node --version)"
IFS=. read -r NODE_MAJOR NODE_MINOR _ <<<"${NODE_VERSION#v}"
if [ "$NODE_MAJOR" -lt 22 ] || { [ "$NODE_MAJOR" -eq 22 ] && [ "$NODE_MINOR" -lt 12 ]; }; then
  die "Found Node.js $NODE_VERSION - 22.12+ is required. Upgrade via nvm: nvm install 24"
fi
ok "Found Node.js $NODE_VERSION"
command -v npm >/dev/null 2>&1 || die "npm is required but not found (it ships with Node.js)."
ok "Found npm v$(npm --version)"
echo ""

# --- STEP 2: venv -------------------------------------------------------------
echo "  --- Setting up Python backend ---"
mkdir -p "$LOG_DIR"
VENV_PY="$VENV_DIR/bin/python"
if [ ! -x "$VENV_PY" ]; then
  warn "Creating virtual environment at src/backend/.venv-linux (first-time setup) ..."
  "$PYTHON" -m venv "$VENV_DIR" || die "Failed to create virtual environment (Debian/Ubuntu: sudo apt install python3-venv)."
  ok "Virtual environment created"
else
  ok "Virtual environment exists"
fi

# --- STEP 3: pip, with dev.ps1's SQLCipher fallback ---------------------------
status "Installing Python dependencies (log: logs/dev-pip.log) ..."
"$VENV_PY" -m pip install --upgrade pip --quiet >/dev/null 2>&1 || true
SQLCIPHER_AVAILABLE=1
PIP_LOG="$LOG_DIR/dev-pip.log"
if ! "$VENV_PY" -m pip install -r "$BACKEND_DIR/requirements.txt" >"$PIP_LOG" 2>&1; then
  if grep -qi sqlcipher "$PIP_LOG"; then
    warn "SQLCipher could not be installed (Debian/Ubuntu: sudo apt install libsqlcipher-dev, then re-run)."
    status "Installing remaining dependencies without SQLCipher ..."
    SQLCIPHER_AVAILABLE=0
    FILTERED="$(mktemp)"
    grep -vi sqlcipher "$BACKEND_DIR/requirements.txt" >"$FILTERED" || true
    "$VENV_PY" -m pip install -r "$FILTERED" --quiet >>"$PIP_LOG" 2>&1 || { rm -f "$FILTERED"; tail -n 15 "$PIP_LOG" >&2; die "pip install failed. See $PIP_LOG"; }
    rm -f "$FILTERED"
    ok "Python dependencies installed (without SQLCipher)"
  else
    tail -n 15 "$PIP_LOG" >&2
    die "Failed to install Python dependencies. See $PIP_LOG"
  fi
else
  ok "Python dependencies installed"
fi

# --- STEP 3b: OCR tools (detect only; no system installs) --------------------
TESSERACT_OK=0
if [ "${HC_SKIP_OCR_SETUP:-}" = "1" ]; then
  status "Skipping OCR setup (HC_SKIP_OCR_SETUP=1)."
else
  if command -v tesseract >/dev/null 2>&1; then TESSERACT_OK=1; ok "Tesseract OCR is available"
  else warn "Tesseract not found. For scanned PDFs: sudo apt install tesseract-ocr  (macOS: brew install tesseract)"; fi
  if command -v pdftoppm >/dev/null 2>&1; then ok "Poppler (pdftoppm) is available"
  else warn "pdftoppm not found - scanned PDF OCR may fail. Install: sudo apt install poppler-utils  (macOS: brew install poppler)"; fi
fi

# --- STEP 4: .env ------------------------------------------------------------
status "Checking .env configuration ..."
if [ ! -f "$ENV_FILE" ]; then
  if [ -f "$ENV_EXAMPLE" ]; then
    cp "$ENV_EXAMPLE" "$ENV_FILE"; ok "Created .env from template"
  else
    printf '%s\n' APP_MODE=local APP_ENV=development DEBUG=true HOST=127.0.0.1 PORT=8000 \
      DATABASE_TYPE=sqlite DATABASE_ENCRYPTION_ENABLED=true DATABASE_ENCRYPTION_REQUIRED=false >"$ENV_FILE"
    ok "Created default .env"
  fi
fi
# Same as dev.ps1: only when SQLCipher failed to install, flip REQUIRED=true to false.
if [ "$SQLCIPHER_AVAILABLE" = "0" ] && grep -Eiq 'DATABASE_ENCRYPTION_REQUIRED[[:space:]]*=[[:space:]]*true' "$ENV_FILE"; then
  TMP_ENV="$(mktemp)"
  sed -E 's/[Dd][Aa][Tt][Aa][Bb][Aa][Ss][Ee]_[Ee][Nn][Cc][Rr][Yy][Pp][Tt][Ii][Oo][Nn]_[Rr][Ee][Qq][Uu][Ii][Rr][Ee][Dd][[:space:]]*=[[:space:]]*[Tt][Rr][Uu][Ee]/DATABASE_ENCRYPTION_REQUIRED=false/g' "$ENV_FILE" >"$TMP_ENV"
  cat "$TMP_ENV" >"$ENV_FILE" && rm -f "$TMP_ENV"
  warn "Set DATABASE_ENCRYPTION_REQUIRED=false (SQLCipher not installed)"
fi
if [ "${HC_SKIP_OCR_SETUP:-}" != "1" ]; then
  if [ "$TESSERACT_OK" = "1" ]; then
    set_env_key "$ENV_FILE" OCR_ENABLED true; ok "Synced .env: OCR_ENABLED=true (Tesseract on PATH)"
  else
    set_env_key "$ENV_FILE" OCR_ENABLED false; warn "Synced .env: OCR_ENABLED=false (Tesseract not detected - install and re-run dev.sh)"
  fi
fi
ok ".env is ready"
echo ""

# --- STEP 5: frontend deps (npm ci only when the lockfile changed) -----------
echo "  --- Setting up frontend ---"
MODULES="$FRONTEND_DIR/node_modules"
MARKER="$MODULES/.asclexis-lockfile.sha256"
LOCKFILE="$FRONTEND_DIR/package-lock.json"
vite_present() { [ -e "$MODULES/.bin/vite" ] && [ -f "$MODULES/vite/bin/vite.js" ]; }
REASON=""
if [ ! -e "$MODULES" ] && [ ! -L "$MODULES" ]; then REASON="missing"
elif ! vite_present; then REASON="incomplete"
elif [ ! -f "$LOCKFILE" ] || [ ! -f "$MARKER" ] || [ "$(lock_hash "$LOCKFILE")" != "$(head -n 1 "$MARKER" | tr -d '[:space:]')" ]; then REASON="lockfile-changed"
fi
if [ -n "$REASON" ]; then
  status "Installing frontend dependencies ($REASON) ..."
  # npm ci empties node_modules; through a link that would empty the folder it points to.
  [ ! -L "$MODULES" ] || die "src/frontend/node_modules is a link to another folder. Nothing was changed. Remove the link (not the folder it points to) and run again."
  rm -f "$MARKER"   # a failed or interrupted install must never look current
  LOCK_HASH=""; [ -f "$LOCKFILE" ] && LOCK_HASH="$(lock_hash "$LOCKFILE")"
  (cd "$FRONTEND_DIR" && npm ci) || die "npm ci failed. Frontend dependencies are not installed."
  vite_present || die "npm ci succeeded but Vite was not found. Delete src/frontend/node_modules and run again."
  printf '%s\n' "$LOCK_HASH" >"$MARKER" || warn "Could not record the installed version; next start will reinstall."
  ok "Frontend dependencies installed"
else
  ok "Frontend dependencies already installed"
fi
echo ""

# --- STEP 6/7: data dirs, ports, .env.local -----------------------------------
mkdir -p "$ROOT_DIR/data/vaults"
echo "  --- Checking ports ---"
# ponytail: no killing of whatever holds 8000/3000 (dev.ps1 does); we just take the next free port.
API_PORT="$(free_port "$BACKEND_PORT")"
WEB_PORT="$(free_port "$FRONTEND_PORT")"
if [ "$API_PORT" = "$BACKEND_PORT" ]; then ok "Port $API_PORT is available (backend)"; else warn "Port $BACKEND_PORT in use - using $API_PORT for backend"; fi
if [ "$WEB_PORT" = "$FRONTEND_PORT" ]; then ok "Port $WEB_PORT is available (frontend)"; else warn "Port $FRONTEND_PORT in use - using $WEB_PORT for frontend"; fi
set_env_key "$FRONTEND_DIR/.env.local" VITE_API_URL "http://localhost:$API_PORT/api/v1"
ok "Synced .env.local: VITE_API_URL=http://localhost:$API_PORT/api/v1"
echo ""

# --- STEP 8: launch -----------------------------------------------------------
BACKEND_LOG="$LOG_DIR/dev-backend.log"
FRONTEND_LOG="$LOG_DIR/dev-frontend.log"
BPID=""; FPID=""
# shellcheck disable=SC2329  # invoked via trap
cleanup() {
  trap - EXIT INT TERM
  echo ""; status "Shutting down ..."
  local pid
  for pid in $BPID $FPID; do kill -TERM -- "-$pid" 2>/dev/null || true; done
  sleep 2
  for pid in $BPID $FPID; do kill -KILL -- "-$pid" 2>/dev/null || true; done
  ok "Servers stopped. Goodbye!"
}
trap cleanup EXIT
trap 'exit 130' INT TERM

# Job control gives each server its own process group, so cleanup can kill the
# uvicorn reloader + worker and node + esbuild as a group. Ctrl+C only reaches this script.
set -m
(cd "$BACKEND_DIR" && exec "$VENV_PY" -m uvicorn main:app --reload --host 127.0.0.1 --port "$API_PORT") >"$BACKEND_LOG" 2>&1 &
BPID=$!
(cd "$FRONTEND_DIR" && exec node "$MODULES/vite/bin/vite.js" --host 127.0.0.1 --port "$WEB_PORT" --strictPort) >"$FRONTEND_LOG" 2>&1 &
FPID=$!
set +m
ok "Backend  started  [PID $BPID]  log: logs/dev-backend.log"
ok "Frontend started  [PID $FPID]  log: logs/dev-frontend.log"

status "Waiting for servers to be ready ..."
READY=0
for _ in $(seq 1 60); do
  kill -0 "$BPID" 2>/dev/null || { tail -n 20 "$BACKEND_LOG" >&2; die "Backend exited during startup."; }
  kill -0 "$FPID" 2>/dev/null || { tail -n 20 "$FRONTEND_LOG" >&2; die "Frontend exited during startup."; }
  if curl -fsS -o /dev/null "http://127.0.0.1:$API_PORT/health" 2>/dev/null && curl -fsS -o /dev/null "http://127.0.0.1:$WEB_PORT/" 2>/dev/null; then
    ok "Servers are ready!"; READY=1; break
  fi
  sleep 1
done
[ "$READY" = "1" ] || warn "Servers are still starting (or curl is missing); check logs/ if a URL does not load."

echo ""
echo "  ============================================="
echo "    Asclexis is running!"
echo "  ============================================="
echo "    Frontend:     http://localhost:$WEB_PORT"
echo "    Backend API:  http://localhost:$API_PORT"
echo "    API Docs:     http://localhost:$API_PORT/docs"
echo ""
echo "    Press Ctrl+C to stop."
echo ""

# ponytail: no auto-restart (dev.ps1 restarts crashed servers); uvicorn --reload covers code edits.
while kill -0 "$BPID" 2>/dev/null && kill -0 "$FPID" 2>/dev/null; do sleep 2; done
kill -0 "$BPID" 2>/dev/null || { warn "Backend stopped. Last log lines:"; tail -n 20 "$BACKEND_LOG" >&2; }
kill -0 "$FPID" 2>/dev/null || { warn "Frontend stopped. Last log lines:"; tail -n 20 "$FRONTEND_LOG" >&2; }
exit 1
