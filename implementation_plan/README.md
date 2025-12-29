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

### MVP Requirements Checklist

| ID | Requirement | Status | Implementation File |
|----|-------------|--------|---------------------|
| MVP-01 | Import text-based lab PDFs | 🔲 Pending | - |
| MVP-02 | Extract analyte rows with provenance | 🔲 Pending | - |
| MVP-03 | User verification UI | 🔲 Pending | - |
| MVP-04 | Per-analyte trend chart | 🔲 Pending | - |
| MVP-05 | Doctor-ready summary export | 🔲 Pending | - |
| MVP-06 | Grounded explanation with citations | 🔲 Pending | - |
| MVP-07 | Local encryption for DB and vault | 🔲 Pending | - |

## Implementation Log

| Date | Feature | Phase | File |
|------|---------|-------|------|
| 2024-12-28 | Project structure setup | 0 | [2024-12-28_project-structure-setup.md](2024-12-28_project-structure-setup.md) |

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
