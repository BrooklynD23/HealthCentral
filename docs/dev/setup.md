# Developer Setup and Commands

**Last Updated:** 2026-10-25
**Owner:** Project Lead
**Refresh Trigger:** A launcher (`dev.ps1`, `dev.sh`), prerequisite, model tier, migration command, or CI test command changes

Moved verbatim from the repository [README](../../README.md) on 2026-10-25 so the README can stay a short entry point. Behavioural rules are in [`CLAUDE.md`](../../CLAUDE.md); the collected-test baseline and the definition of done are in [`AGENT.md`](../../AGENT.md).

## Prerequisites
- Python 3.11+
- Node.js 22.12+ (Node.js 24 LTS recommended)
- Browser: Safari 16.4+, Chrome 111+, Firefox 128+
- Optional: Tesseract and Poppler (`pdftoppm`) for OCR of scanned documents

## Quick Start (Windows, `dev.ps1`)

Windows is the native development environment. From the repository root:

```powershell
.\dev.bat        # one-click launcher
.\dev.ps1        # or run the PowerShell script directly
```

`dev.ps1`:
- checks for Python and Node.js;
- creates the backend virtual environment at `src/backend/venv` if needed and installs `requirements.txt`. **If `sqlcipher3-binary` cannot be installed, it installs the rest, sets `DATABASE_ENCRYPTION_REQUIRED=false` in `src/backend/.env` and warns: profile databases are then unencrypted, so do not use real data** (see [SQLCipher Setup](#sqlcipher-setup));
- runs `npm ci` when `src/frontend/package-lock.json` changes;
- creates the data directory structure and `.env`;
- resolves the next free backend/frontend ports if 8000/3000 are busy and syncs `src/frontend/.env.local` with the resolved API URL;
- starts both servers and opens the browser.

Default URLs: frontend http://localhost:3000, backend http://localhost:8000
(`/docs` serves the interactive API docs when `DEBUG=true`). If a port is busy,
use the URLs `dev.ps1` prints. `Ctrl+C` stops both servers.

## Quick Start on WSL/Linux (`dev.sh`)

Clone into your Linux home (for example `~/HealthCentral`), **not** under `/mnt/c`: the Windows mount is slow, file watching is unreliable, and Windows and Linux cannot share the venv or `node_modules`. `dev.sh` refuses to run from `/mnt/*` unless `HC_ALLOW_WINDOWS_MOUNT=1` is set.

```bash
git clone <repo-url> ~/HealthCentral && cd ~/HealthCentral
./dev.sh
```

It mirrors `dev.ps1`, with these differences:
- Uses its own venv at `src/backend/.venv-linux` (never the Windows `src/backend/venv`).
- Never installs system packages; it prints an install hint when Python 3.11+, Node.js 22.12+, `tesseract` or `pdftoppm` is missing.
- Picks the next free port when 8000/3000 are busy, but does not stop the process holding them.
- Binds both servers to `127.0.0.1`, writes `logs/dev-backend.log` and `logs/dev-frontend.log`, does not open a browser and does not restart a crashed server.

## Model setup

The app works without any model: the assistant falls back to a no-LLM
knowledge path, and the agent path makes no model call. A local model enables
the legacy RAG explainer and model-backed interpretations. Run these from
`src/backend` (`scripts/download_models.py`):

```bash
python scripts/download_models.py list                   # tiers, RAM/disk needs, download status, Ollama tags
python scripts/download_models.py auto                   # download the tier recommended for this hardware
python scripts/download_models.py download --tier mid    # or a specific tier (low, mid, high, gemma4-*)
python scripts/download_models.py embedding              # one-time fetch of the embedding bundle (needed for retrieval)
python scripts/download_models.py nli                    # optional: NLI cross-encoder (HC-M11, flag-gated)
```

- **llama.cpp (default).** `LLM_PROVIDER=llama_cpp` loads GGUF files from
  `models/` in-process. The Gemma 4 tier repos are marked as placeholders in
  `download_models.py`; `python scripts/download_models.py verify` checks every
  tier repo exists on Hugging Face (needs network).
- **Ollama.** Set `LLM_PROVIDER=ollama` and `LLM_MODEL` (for example
  `gemma4:12b`), and pull the model with
  `ollama pull <tag>` or `python scripts/download_models.py ollama --tag <tag>`.
  The provider connects to the local default `127.0.0.1:11434`, and switching
  provider in Settings rejects a non-localhost `OLLAMA_BASE_URL`. If the daemon
  is unreachable the factory falls back to llama.cpp. The provider
  can also be switched in Settings (`PUT /api/v1/settings/model/provider`).
- **Embedding bundle.** The pinned `all-MiniLM-L6-v2` revision is fetched once,
  sha256-checked per file, and loaded with `local_files_only=True`; the backend
  never downloads it at runtime and fails closed if it is absent. Without it,
  exactly 5 backend tests fail (see [AGENT.md](../../AGENT.md#commands-windows-is-the-native-dev-environment)).

Configuration lives in `src/backend/.env`, created from
[`config/.env.example`](../../config/.env.example).

## SQLCipher Setup

Each profile database is an AES-256 SQLCipher database. `sqlcipher3-binary`
(in `requirements.txt`) ships pre-built wheels; on Debian/Ubuntu install
`libsqlcipher-dev` first if the wheel fails to build, and on macOS
`brew install sqlcipher`. Verify with:

```python
import sqlcipher3
print(sqlcipher3.connect(":memory:").execute("PRAGMA cipher_version").fetchone())  # ('4.x.x',)
```

`DATABASE_ENCRYPTION_REQUIRED=false` in `.env` allows unencrypted profile
databases for development only. **Never use it with real data.**

## Database migrations

Two independent Alembic chains: `migrations/master/` (profiles, audit log,
knowledge base) and `migrations/profile/` (each SQLCipher vault). Master
migrations run on startup; profile migrations run when a vault is opened.
Databases without `alembic_version` are stamped, not migrated. Manual use, from
`src/backend`:

```bash
python -m scripts.migrate master                          # master chain
python -m scripts.migrate status                          # migration status
python -m scripts.migrate profile --profile-id <uuid>     # one profile (prompts for its password)
```

## Running tests

```bash
# Backend (from src/backend)
python -m pytest tests/ -p no:cacheprovider -q

# Frontend (from src/frontend)
npx tsc --noEmit
npx vitest run
npx playwright test --project chromium       # e2e, as CI runs it

# Eval gates, docs and hygiene (from the repo root, as CI runs them)
python3 scripts/agent_eval_gate.py           # CI: Agent Eval Gate
python3 scripts/legacy_eval_gate.py          # CI: Legacy RAG Eval Gate
python3 scripts/docs_lint.py
python3 scripts/repo_hygiene_check.py
```

The current collected-test baseline and the known environment-only failures
are recorded in [`AGENT.md`](../../AGENT.md#commands-windows-is-the-native-dev-environment);
the full definition of done is in [`AGENT.md`](../../AGENT.md#definition-of-done).
On WSL with a Windows-mounted checkout, clear `__pycache__` before pytest and
prefer running the frontend toolchain on Windows. The contributor proof bundle
is in [`CONTRIBUTING.md`](../../CONTRIBUTING.md).

## Supported Local Verification Bootstrap (WSL/Linux)

Creates the repo-root verifier environment that the contributor proof bundle
expects. Run from the repository root, with a venv created by the WSL/Linux
interpreter (never activate a Windows-created venv from `/mnt/c/...`):

```bash
python3 -m venv .wsl-pytest-venv
./.wsl-pytest-venv/bin/python -m pip install --upgrade pip
./.wsl-pytest-venv/bin/python -m pip install -r src/backend/requirements.txt
npm --prefix src/frontend install

python3 scripts/docs_lint.py
npx --prefix src/frontend tsc --noEmit -p src/frontend/tsconfig.json
PYTHONPATH=src/backend ./.wsl-pytest-venv/bin/python -m pytest src/backend/tests/test_bootstrap_check.py -q
```

`.wsl-pytest-venv/` and `.bg-shell/` are local-only and gitignored. If
`sqlcipher3-binary` fails to install on Debian/Ubuntu, install
`libsqlcipher-dev` first. OCR-heavy tests and features also need
`tesseract-ocr` and Poppler; the bootstrap smoke test does not.

## Full UI verification (optional)

The manual sweep in
[`src/frontend/e2e/BROWSER_MCP_PLAYBOOK.md`](../../src/frontend/e2e/BROWSER_MCP_PLAYBOOK.md),
and the real-PDF Playwright project (`--project real-pdf-local`, set
`HC_E2E_REAL_PDF`; see
[`src/frontend/e2e/ui-full-verification.spec.ts`](../../src/frontend/e2e/ui-full-verification.spec.ts)).

## Manual development

```bash
# Terminal 1: backend (from src/backend, inside its venv)
uvicorn main:app --reload --host 127.0.0.1 --port 8000

# Terminal 2: frontend (from src/frontend)
npm run dev
```
