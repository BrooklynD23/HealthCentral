# HealthCentral Project Overview

## Purpose
HealthCentral is a **local-first medical results companion** application for patients to:
- Import lab PDFs and medical documents into a secure local vault
- Extract & verify structured data with human-in-the-loop verification
- Visualize longitudinal trends with reference range context
- Understand results via grounded explanations with citations (local RAG)
- Export doctor-ready summaries and discussion prompts

## Core Principles
- **Local-First**: All data stays on device by default
- **Privacy-First**: Encrypted at rest; no network calls required
- **Grounded Outputs**: Every claim cites user documents or curated references
- **Conservative Behavior**: Prefer "insufficient information" over speculation
- **No Medical Advice**: Education only; no diagnosis or treatment recommendations

## Tech Stack

### Backend (Python 3.11+)
- **Framework**: FastAPI
- **Database**: SQLite + SQLCipher (encrypted), SQLAlchemy 2.0
- **Vector Store**: sqlite-vss or FAISS (encrypted)
- **Local LLM**: llama.cpp with GGUF models
- **Embeddings**: bge-small-en or e5-small
- **PDF Processing**: pdfplumber, pypdf

### Frontend
- **Framework**: React 18 with TypeScript
- **State Management**: TanStack Query (React Query)
- **Styling**: Tailwind CSS
- **Build**: Vite

### Desktop Shell (Future)
- Tauri (Rust + WebView)

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
│   │   └── models/           # Database models (NOT YET CREATED)
│   └── frontend/             # React/TypeScript frontend
│       └── src/
│           ├── components/   # UI components
│           ├── pages/        # Page components
│           ├── services/     # API services
│           └── hooks/        # Custom React hooks
├── config/                   # Configuration templates
└── data/                     # Local data directory (gitignored)
```

## Current Development Status
- Branch: `Security-Revamp`
- Stage: Early MVP development
- **Critical Issue**: `models/` directory doesn't exist yet - app cannot start
