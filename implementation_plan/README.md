# Implementation Plan

This folder tracks the implementation progress of HealthCentral features.

## Structure

Each implemented feature is documented in a separate markdown file with:
- **Date**: Implementation date
- **Feature**: Short description
- **Status**: Completed / In Progress / Planned
- **Phase**: Which PRD phase (0-4)
- **Details**: Technical implementation notes

## Naming Convention

Files follow this pattern:
```
YYYY-MM-DD_feature-short-name.md
```

Example: `2024-12-28_project-structure-setup.md`

## Current Phase: Phase 0 (MVP)

Focus: Labs from text-based PDFs, offline operation

Execution backlog (tickets + acceptance criteria + E2E matrix):
- `docs/06_mvp_to_rag_execution_board.md`

### MVP Requirements Checklist

| ID | Requirement | Status | Sprint |
|----|-------------|--------|--------|
| MVP-01 | Import text-based lab PDFs | âœ… Complete | Sprint 2 |
| MVP-02 | Extract analyte rows with provenance | âœ… Complete | Sprint 2 |
| MVP-03 | User verification UI | âœ… Complete | Sprint 3 |
| MVP-04 | Per-analyte trend chart | âœ… Complete | Sprint 3 |
| MVP-05 | Doctor-ready summary export | âœ… Complete | Sprint 4 |
| MVP-06 | Grounded explanation with citations | â³ Next | Sprint 5 |
| MVP-07 | Local encryption for DB and vault | âœ… Complete | Sprint 1 |

### Sprint Progress

| Sprint | Focus | Status |
|--------|-------|--------|
| Sprint 1 | Auth + Session Plumbing | âœ… Complete |
| Sprint 2 | Import â†’ Extract â†’ Normalize â†’ Persist | âœ… Complete |
| Sprint 3 | Verification Workbench + Trends Dashboard | âœ… Complete |
| Sprint 4 | Export System End-to-End | âœ… Complete |
| Sprint 5 | RAG Assistant (Post-MVP) | â³ **NEXT** |

## Implementation Log

| Date | Feature | Phase | File |
|------|---------|-------|------|
| 2026-02-04 | Dual Alembic migrations | 0 | [2026-02-04_alembic-dual-migrations.md](2026-02-04_alembic-dual-migrations.md) |
| 2024-12-28 | Project structure setup | 0 | [2024-12-28_project-structure-setup.md](2024-12-28_project-structure-setup.md) |
| 2026-01-31 | MVPâ†’RAG execution board | 0 | `docs/06_mvp_to_rag_execution_board.md` |

## Architecture Notes

### Local-Only (Current Focus)
- All services run on localhost
- SQLite + SQLCipher for encrypted storage
- llama.cpp for local inference
- No network calls required

### Database Migrations (Alembic)
- Dual-environment setup: `migrations/master/` and `migrations/profile/`
- Baseline detection for safe rollout to existing installations
- Non-blocking execution via `asyncio.to_thread()`
- SQLCipher-aware profile migrations with PRAGMA key support
- CLI tool: `python -m scripts.migrate [master|profile|status]`

### Future Scalability Considerations
- API layer designed for REST/GraphQL exposure
- Database abstraction for future PostgreSQL migration
- Service layer separation for microservices transition
- Configuration-based feature flags for deployment modes

