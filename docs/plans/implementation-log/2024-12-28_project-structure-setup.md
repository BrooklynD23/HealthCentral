# Project Structure Setup

> Historical Reference: this plan predates later implementation work and contains completed items.
> Use `docs/features/TASK_LIST.md` for active remaining tasks.

**Date**: 2024-12-28  
**Phase**: 0 (MVP Foundation)  
**Status**: ✅ Completed  

## Summary

Initial project directory structure and scaffolding for HealthCentral local-first medical results companion.

## Changes Made

### Directory Structure Created

```
HealthCentral/
├── README.md                  # Project overview and setup instructions
├── implementation_plan/       # Feature implementation tracking
│   ├── README.md             # Implementation plan overview
│   └── 2024-12-28_*.md       # Feature implementation logs
├── src/
│   ├── backend/              # Python FastAPI backend
│   │   ├── api/              # API routes
│   │   ├── core/             # Core config, security, database
│   │   ├── modules/          # Feature modules
│   │   ├── models/           # Data models and schemas
│   │   ├── services/         # Business logic
│   │   ├── main.py           # Application entry point
│   │   └── requirements.txt  # Python dependencies
│   ├── frontend/             # Web UI (placeholder)
│   ├── shared/               # Shared types/utilities
│   └── desktop/              # Tauri desktop shell (placeholder)
├── tests/                    # Test suites
├── scripts/                  # Build and utility scripts
├── config/                   # Configuration templates
└── .gitignore               # Git ignore rules
```

### Key Files Created

1. **Backend scaffolding** with modular architecture
2. **Configuration system** supporting local/future deployments
3. **Database abstraction** for SQLite now, PostgreSQL later
4. **API structure** following REST conventions

## Technical Decisions

### Architecture Choices

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Backend Framework | FastAPI | Async, type hints, auto-docs, easy to deploy |
| Database (Local) | SQLite + SQLCipher | Encrypted, portable, no server needed |
| API Style | REST | Simple, well-understood, future GraphQL option |
| Config Management | Pydantic Settings | Type-safe, env var support |

### Scalability Provisions

- **Abstracted database layer**: Repository pattern allows swapping SQLite → PostgreSQL
- **Service layer separation**: Business logic decoupled from API routes
- **Configuration profiles**: Local vs. server deployment modes
- **Modular structure**: Each feature in separate module for maintainability

## Next Steps

1. Implement core database models (profiles, documents, observations)
2. Set up SQLCipher encryption layer
3. Build document ingestion module
4. Create PDF parsing pipeline

## Related PRD Sections

- Section 10: Proposed Architecture
- Section 11: Data Model
