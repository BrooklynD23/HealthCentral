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
├── docs/                      # PRD and architecture documentation
├── implementation_plan/       # Feature implementation tracking
├── src/
│   ├── backend/              # Python FastAPI backend services
│   │   ├── api/              # API routes and endpoints
│   │   ├── core/             # Core configuration and security
│   │   ├── modules/          # Feature modules (ingest, extract, etc.)
│   │   ├── models/           # Database models and schemas
│   │   └── services/         # Business logic services
│   ├── frontend/             # Web UI (Tauri/Electron shell)
│   │   ├── src/
│   │   └── public/
│   ├── shared/               # Shared types and utilities
│   └── desktop/              # Desktop shell (Tauri)
├── data/                     # Local data directory (gitignored)
├── models/                   # Local AI models (gitignored)
├── tests/                    # Test suites
├── scripts/                  # Build and utility scripts
└── config/                   # Configuration templates
```

## Technology Stack

### Current (Local-Only MVP)
- **Backend**: Python 3.11+ with FastAPI
- **Database**: SQLite + SQLCipher (encrypted)
- **Vector Store**: sqlite-vss or FAISS (encrypted)
- **Local LLM**: llama.cpp with GGUF models
- **Embeddings**: bge-small-en or e5-small
- **Desktop Shell**: Tauri (Rust + WebView)

### Future Scalability
Architecture designed for:
- Web-based deployment (FastAPI → cloud hosting)
- Mobile apps (shared API layer)
- Multi-user support with authentication
- Cloud storage options (opt-in)

## Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+ (for frontend)
- Rust (for Tauri desktop shell - optional for web dev)

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

- [Product Requirements (PRD)](docs/Local_First_Medical_Results_Companion_PRD_v0_1.md)
- [Backend Architecture](docs/01_backend_architecture_plan.md)
- [Frontend & Accessibility](docs/02_frontend_accessibility_plan.md)
- [Data Confidentiality](docs/03_data_confidentiality_pipeline_plan.md)
- [Backend Integration Status](docs/05_backend_integration_status.md)
- [Local AI Models](docs/04_local_models_inference_plan.md)

## Implementation Progress

See [implementation_plan/](implementation_plan/) for detailed feature tracking.

## License

[TBD]

## Disclaimer

This application is for informational and educational purposes only. It does not provide medical advice, diagnosis, or treatment recommendations. Always consult with qualified healthcare professionals for medical decisions.
