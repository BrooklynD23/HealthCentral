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
| MVP-01 | Import text-based lab PDFs | ✅ Complete | Sprint 2 |
| MVP-02 | Extract analyte rows with provenance | ✅ Complete | Sprint 2 |
| MVP-03 | User verification UI | ✅ Complete | Sprint 3 |
| MVP-04 | Per-analyte trend chart | ✅ Complete | Sprint 3 |
| MVP-05 | Doctor-ready summary export | ✅ Complete | Sprint 4 |
| MVP-06 | Grounded explanation with citations | ⏳ Next | Sprint 5 |
| MVP-07 | Local encryption for DB and vault | ✅ Complete | Sprint 1 |

### Sprint Progress

| Sprint | Focus | Status |
|--------|-------|--------|
| Sprint 1 | Auth + Session Plumbing | ✅ Complete |
| Sprint 2 | Import → Extract → Normalize → Persist | ✅ Complete |
| Sprint 3 | Verification Workbench + Trends Dashboard | ✅ Complete |
| Sprint 4 | Export System End-to-End | ✅ Complete |
| Sprint 5 | RAG Assistant (Post-MVP) | ⏳ **NEXT** |

## Implementation Log

| Date | Feature | Phase | File |
|------|---------|-------|------|
| 2024-12-28 | Project structure setup | 0 | [2024-12-28_project-structure-setup.md](2024-12-28_project-structure-setup.md) |
| 2026-01-31 | MVP→RAG execution board | 0 | `docs/06_mvp_to_rag_execution_board.md` |

## Architecture Notes

### Local-Only (Current Focus)
- All services run on localhost
- SQLite + SQLCipher for encrypted storage
- llama.cpp for local inference
- No network calls required

### Future Scalability Considerations
- API layer designed for REST/GraphQL exposure
- Database abstraction for future PostgreSQL migration
- Service layer separation for microservices transition
- Configuration-based feature flags for deployment modes
