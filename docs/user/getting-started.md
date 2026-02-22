# Getting Started

## Prerequisites

- Python 3.11 or later
- Node.js 20 or later
- SQLCipher library (`libsqlcipher-dev` on Ubuntu/Debian)

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/HealthCentral.git
cd HealthCentral
```

### 2. Install Backend Dependencies

```bash
pip install -r src/backend/requirements.txt
```

### 3. Install Frontend Dependencies

```bash
cd src/frontend
npm install
```

### 4. Install SQLCipher (Linux)

```bash
sudo apt-get install -y libsqlcipher-dev
```

On macOS:
```bash
brew install sqlcipher
```

## First Launch

### Start the Backend

```bash
cd src/backend
python main.py
```

The API starts at `http://localhost:8000`. Health check: `http://localhost:8000/health`

### Start the Frontend

```bash
cd src/frontend
npm run dev
```

The app opens at `http://localhost:3000`.

## Creating Your First Profile

1. Open the app at `http://localhost:3000`
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
