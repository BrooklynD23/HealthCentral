# Backend Integration Status

**Last Updated:** 2026-03-27
**Owner:** Backend/platform maintainers
**Refresh Trigger:** Sprint-06 baseline framing changes or audit follow-up updates
**Status:** Historical Reference — Sprint 06 integration snapshot retained for audit context

> Historical Reference: this document captures the Sprint 06 integration baseline that was audited in M001/S01. It is retained for delivery history and audit context, and is **not** the source of truth for the live API surface.

---

## Current source of truth

Use these docs for current-state work:

1. `README.md` — repo entrypoint and audited live feature surface overview.
2. `docs/api/endpoints.md` — exact mounted live backend routes; this is the API source of truth.
3. `docs/features/TASK_LIST.md` — active remaining-work tracker and canonical ownership order.
4. `.gsd/milestones/M001/slices/S01/S01-ASSESSMENT.md` — audit evidence explaining where snapshot drift was found.

---

## What this Sprint 06 snapshot captured accurately

The Sprint 06 baseline remains useful historical context for the work that shipped in the platform/compliance pass:

- Security middleware hardening (`input validation`, `rate limiting`, `security headers`, `security audit logging`).
- Monitoring and liveness surfaces (`/health`, authenticated metrics, correlation IDs, timing headers).
- Backup/restore utility support.
- Stabilization fixes around OCR fallback behavior, config validation, and deterministic assistant fallback behavior.
- The general backend/frontend integration shape for profiles, documents, observations, interpretations, medications, notifications, export, and core model settings.

---

## Audit-confirmed drift from the live mounted surface

M001/S01 verified that the live router inventory in `src/backend/api/__init__.py` goes beyond the old Sprint 06 snapshot. The snapshot was therefore competing with more current docs until this reconciliation pass.

Notable live surfaces that were under-documented or absent in the snapshot:

- **memory** CRUD under `/api/v1/memory/*`.
- **gamification** beyond badge listing, including `/api/v1/gamification/streaks`.
- **model settings** sub-surfaces for external API config, timezone, and voice preferences.
- Document classification, extracted entities, and page-image rendering under `/api/v1/documents/{id}/category`, `/entities`, and `/pages/{page_number}/image`.
- The exact live profile/auth surface (`/profiles/login`, `/profiles/me`, `/profiles/logout`, `/profiles/{id}/change-password`).

The audit also confirmed that some previously documented advanced paths were stale. For example, the live medication router exposes `learn-patterns`; it does **not** currently mount a medication correlations endpoint.

---

## Why this file still exists

This file is retained because it helps future contributors answer historical questions such as:

- what Sprint 06 claimed to deliver,
- what backend/frontend integration shape existed at that checkpoint,
- and why newer docs now point elsewhere for the live surface.

Treat it as a frozen baseline narrative, not as an active tracker.
