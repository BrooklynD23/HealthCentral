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

## Current Phase: Post-MVP (Feature Expansion + Operations)

All MVP requirements are complete. Current work is feature expansion, quality, and operational infrastructure.

For active remaining work, see [`docs/features/TASK_LIST.md`](../docs/features/TASK_LIST.md).

### MVP Requirements Checklist

| ID | Requirement | Status | Sprint |
|----|-------------|--------|--------|
| MVP-01 | Import text-based lab PDFs | Done | Sprint 2 |
| MVP-02 | Extract analyte rows with provenance | Done | Sprint 2 |
| MVP-03 | User verification UI | Done | Sprint 3 |
| MVP-04 | Per-analyte trend chart | Done | Sprint 3 |
| MVP-05 | Doctor-ready summary export | Done | Sprint 4 |
| MVP-06 | Grounded explanation with citations | Done | RAG Sprint |
| MVP-07 | Local encryption for DB and vault | Done | Sprint 1 |

### Sprint Progress

| Sprint | Focus | Status |
|--------|-------|--------|
| Sprint 1 | Auth + Session Plumbing | Done |
| Sprint 2 | Import, Extract, Normalize, Persist | Done |
| Sprint 3 | Verification Workbench + Trends Dashboard | Done |
| Sprint 4 | Export System + Data Interoperability | Done |
| Sprint 5 | Frontend Quality and Testing (188 tests) | Done |
| Sprint 6 | Platform Operations and Compliance | Done |

## Implementation Log

| Date | Feature | Phase | File |
|------|---------|-------|------|
| 2024-12-28 | Project structure setup | 0 | [2024-12-28_project-structure-setup.md](2024-12-28_project-structure-setup.md) |
| 2026-02-04 | Dual Alembic migrations | 0 | [2026-02-04_alembic-dual-migrations.md](2026-02-04_alembic-dual-migrations.md) |
| 2026-06-11 | Agent overhaul plan | 2 | [2026-06-11_agent-overhaul-plan.md](2026-06-11_agent-overhaul-plan.md) |
| 2026-06-11 | Breakage map | 2 | [2026-06-11_breakage-map.md](2026-06-11_breakage-map.md) |
| 2026-06-11 | Verification report | 2 | [2026-06-11_verification-report.md](2026-06-11_verification-report.md) |

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
