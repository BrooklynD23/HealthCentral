# HealthCentral

**Local-First Medical Results Companion**

A privacy-first desktop application for patients to import medical documents, extract structured information with user verification, visualize trends, and generate grounded explanations with citations.

## Overview

HealthCentral helps patients:
- **Import** lab PDFs and medical documents into a secure local vault
- **Extract & Verify** structured data with human-in-the-loop verification
- **Visualize** longitudinal trends with reference range context
- **Understand** results via grounded explanations with citations (local RAG)
- **Export** doctor-ready summaries and discussion prompts

## Core Principles

- **Local-First**: All data stays on your device by default
- **Privacy-First**: Encrypted at rest; no network calls required
- **Grounded Outputs**: Every claim cites user documents or curated references
- **Conservative Behavior**: Prefer "insufficient information" over speculation
- **No Medical Advice**: Education only; no diagnosis or treatment recommendations

## Project Structure

```
HealthCentral/
├── docs/                      # Architecture and feature documentation
│   ├── api/                   # API endpoint documentation
│   ├── user/                  # User guides, workflows, FAQ
│   ├── compliance/            # HIPAA, data privacy, audit checklist
│   ├── features/              # Feature architecture + active task list
│   └── model_tiers/           # AI model tier documentation
├── src/
│   ├── backend/              # Python FastAPI backend
│   │   ├── api/              # API routes and endpoints
│   │   ├── core/             # Core config, security, database
│   │   ├── models/           # SQLAlchemy database models
│   │   ├── modules/          # Feature modules (ingest, RAG, etc.)
│   │   ├── monitoring/       # Metrics, correlation IDs, timing
│   │   ├── security/         # Input validation, rate limiting, headers
│   │   ├── scripts/          # Backup, migrations, model management
│   │   └── tests/            # Backend test suites
│   └── frontend/             # React + Vite + TypeScript
│       ├── src/
│       └── public/
├── config/                   # Configuration templates (.env.example)
├── data/                     # Local data directory (gitignored)
├── models/                   # Local AI models (gitignored)
└── scripts/                  # Build and utility scripts
```

## Technology Stack

### Current (Local-Only MVP)
- **Backend**: Python 3.11+ with FastAPI
- **Database**: SQLite + SQLCipher (encrypted)
- **Vector Store**: sqlite-vss or FAISS (encrypted)
- **Local LLM**: llama.cpp with GGUF models
- **Embeddings**: bge-small-en or e5-small
- **Frontend**: React + Vite + TypeScript

### Future Scalability
Architecture designed for:
- Web-based deployment (FastAPI → cloud hosting)
- Mobile apps (shared API layer)
- Multi-user support with authentication
- Cloud storage options (opt-in)

## SQLCipher Setup (Required for Database Encryption)

HealthCentral uses SQLCipher for encrypted per-profile databases. Each user profile has its own AES-256 encrypted SQLite database.

### Installation

#### Windows (Recommended: pre-built wheel)
```powershell
pip install sqlcipher3-binary
```

#### Linux (Debian/Ubuntu)
```bash
sudo apt-get install libsqlcipher-dev
pip install sqlcipher3-binary
```

#### macOS
```bash
brew install sqlcipher
pip install sqlcipher3-binary
```

### Verify Installation
```python
import sqlcipher3
conn = sqlcipher3.connect(":memory:")
cursor = conn.cursor()
cursor.execute("PRAGMA cipher_version")
print(cursor.fetchone())  # Should print ('4.x.x',)
```

### Development Without SQLCipher
If you cannot install SQLCipher, set in `.env`:
```
DATABASE_ENCRYPTION_REQUIRED=false
```
**WARNING:** Profile databases will be unencrypted. Never use in production.

## Database Migrations

HealthCentral uses **Alembic** for database schema migrations with a dual-environment setup:

- **Master database**: Profiles, audit logs, knowledge base (unencrypted)
- **Profile databases**: Per-user SQLCipher encrypted vaults

### Running Migrations

```powershell
cd src\backend

# Run master database migrations
python -m scripts.migrate master

# Check migration status
python -m scripts.migrate status

# Run profile migrations (requires password)
python -m scripts.migrate profile --profile-id <uuid>
```

### Safe Rollout

The migration system includes **baseline detection**:
- Existing databases without `alembic_version` are stamped (not migrated)
- This prevents "table already exists" errors on existing installations
- New installations get full schema creation via migrations

Migrations run automatically:
- Master migrations run on application startup
- Profile migrations run when a vault is opened

## Getting Started

### Prerequisites
- Python 3.11+
- Node.js 18+ (for frontend)

### Quick Start (Recommended)

The easiest way to start development is using the included dev script:

```powershell
# From the project root directory
.\dev.bat

# Or directly with PowerShell
.\dev.ps1
```

This script automatically:
- Checks for Python and Node.js installations
- Creates a Python virtual environment if needed
- Installs all dependencies (pip and npm)
- Creates the data directory structure
- Starts both backend and frontend servers

Once running:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

Press `Ctrl+C` to stop both servers.

### Manual Installation

If you prefer manual setup:

```bash
# Clone repository
git clone https://github.com/your-org/HealthCentral.git
cd HealthCentral

# Backend setup
cd src/backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt

# Frontend setup
cd ../frontend
npm install
```

### Manual Development

```bash
# Terminal 1: Start backend
cd src/backend
venv\Scripts\activate
uvicorn main:app --reload --host 127.0.0.1 --port 8000

# Terminal 2: Start frontend
cd src/frontend
npm run dev
```

## Documentation

### For Users
- [Getting Started](docs/user/getting-started.md)
- [Workflows](docs/user/workflows.md)
- [Troubleshooting](docs/user/troubleshooting.md)
- [FAQ](docs/user/faq.md)

### For Developers
- [API Documentation](docs/api/README.md)
- [Backend Integration Status](docs/05_backend_integration_status.md)
- [Backend Architecture](docs/01_backend_architecture_plan.md)
- [Documentation Index](docs/00_architecture_plans_index.md)

### Compliance & Operations
- [HIPAA Controls](docs/compliance/hipaa-controls.md)
- [Data Privacy](docs/compliance/data-privacy.md)
- [Disaster Recovery](docs/compliance/disaster-recovery.md)
- [Audit Checklist](docs/compliance/audit-checklist.md)

## API Overview

HealthCentral exposes a REST API via FastAPI at `http://localhost:8000/api/v1`. Interactive docs are available at `http://localhost:8000/docs`.

| Group | Endpoints | Description |
|-------|-----------|-------------|
| **Profiles** | `/profiles/` | Create, list, unlock, and lock encrypted user profiles |
| **Documents** | `/documents/` | Import PDFs/images, list, view pages, delete |
| **Observations** | `/observations/` | List, verify, trend analysis, panel grouping |
| **Assistant** | `/assistant/` | RAG chat with citations, test intent lookup, glossary |
| **Interpretations** | `/interpretations/` | Lab and panel interpretation with LLM support |
| **Medications** | `/medications/` | CRUD, schedules, dose logging, adherence stats |
| **Notifications** | `/notifications/` | Reminder settings, history, scheduler status |
| **Export** | `/export/` | CSV/JSON export, doctor summary, discussion questions |
| **Settings** | `/settings/model/` | Model tier selection, hardware detection, downloads |
| **Monitoring** | `/health`, `/monitoring/` | Health check, metrics dashboard |

For full endpoint details, see [API Documentation](docs/api/endpoints.md).

## Implementation Progress

See [docs/features/TASK_LIST.md](docs/features/TASK_LIST.md) for the active remaining-work tracker.

## License

[TBD]

## Disclaimer

This application is for informational and educational purposes only. It does not provide medical advice, diagnosis, or treatment recommendations. Always consult with qualified healthcare professionals for medical decisions.
