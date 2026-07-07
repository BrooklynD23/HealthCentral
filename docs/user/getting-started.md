# Getting Started

## Prerequisites

- Python 3.11 or later
- Node.js 22 or later (Node.js 24 LTS recommended)
- SQLCipher library (`libsqlcipher-dev` on Ubuntu/Debian)

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/HealthCentral.git
cd HealthCentral
```

### 2. Recommended Development Launch

On Windows, use the repo launcher from the project root:

```powershell
.\dev.bat

# Or directly with PowerShell
.\dev.ps1
```

The launcher checks prerequisites, installs backend/frontend dependencies, creates local data directories, resolves ports, writes the frontend `VITE_API_URL` override, and starts both servers. Defaults are `http://localhost:3000` for the app and `http://localhost:8000` for the API, but if either port is busy the launcher selects the next free port and prints the resolved URLs.

### 3. Manual Backend Dependencies

```bash
pip install -r src/backend/requirements.txt
```

### 4. Manual Frontend Dependencies

```bash
npm --prefix src/frontend install
```

### 5. Install SQLCipher (Linux)

```bash
sudo apt-get install -y libsqlcipher-dev
```

On macOS:
```bash
brew install sqlcipher
```

## First Launch

### Start Both Servers

```powershell
.\dev.ps1
```

Use the app/API URLs printed by the launcher. The health check is available at the printed backend URL plus `/health`.

### Manual Backend

```bash
cd src/backend
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

### Manual Frontend

```bash
cd src/frontend
npm run dev
```

Manual defaults are `http://localhost:3000` for the app and `http://localhost:8000` for the API. If you change the backend port manually, set `src/frontend/.env.local` with `VITE_API_URL=http://localhost:<port>/api/v1` before starting Vite.

## Creating Your First Profile

1. Open the app URL printed by `dev.ps1`, or `http://localhost:3000` for a manual default launch
2. Click **Create Profile**
3. Enter your name and a strong password
4. Your encrypted vault is created automatically
5. You are logged in and ready to import documents

## Profile Security

- Each profile has its own encrypted database (SQLCipher)
- Your password never leaves your device
- Auto-lock after 15 minutes of inactivity (configurable)
- All data stored locally in `data/` directory

## Configuration

Settings can be customized via environment variables or a `.env` file in
`src/backend/`:

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_MODE` | `local` | `local` or `server` |
| `DEBUG` | `true` | Enable debug mode and API docs |
| `PORT` | `8000` | API server port |
| `AUTO_LOCK_TIMEOUT_MINUTES` | `15` | Auto-lock timeout |
| `LOG_LEVEL` | `INFO` | Logging verbosity |
| `OCR_ENABLED` | `false` | Enable OCR for images (requires Tesseract) |

## Next Steps

- [Import your first lab results](workflows.md#importing-documents)
- [Review extracted observations](workflows.md#reviewing-observations)
- [Set up medications](workflows.md#medication-management)
