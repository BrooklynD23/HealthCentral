# Product Rename: Surface Audit + Candidate Shortlist (HC-M10, stage 1)

Owner decision (2026-07-07): rename the product — "HealthCentral" collides with the existing health-media brand healthcentral.com. This document is stage 1 of the plan: how big the rename is, and a screened candidate shortlist. **Stage 2 (blocking, manual): the owner picks a candidate and clears it against USPTO TESS + domain registrar + app stores.** Stage 3 executes the rename in one PR.

## Rename surface (audited 2026-07-07)

Occurrences of "HealthCentral" (case-insensitive), by area:

| Area | Count | Category |
|------|-------|----------|
| `docs/` | 181 | Mostly historical plans/logs — **never touched**; product-presenting docs (README-adjacent, user guides) change |
| `src/backend` | 76 | Mostly docstrings/comments (internal, optional); **user-visible: `main.py:67` FastAPI `title="HealthCentral API"`** |
| `README.md` | 18 | Must change (headers, prose) |
| `src/frontend/src` | 9 | Must change — App.tsx, Sidebar.tsx, DocumentInbox, NotificationSettings, ProfileSetup, ExportPage, api.ts, authStore.ts |
| `scripts/` | 8 | Banners/comments (low priority) |
| `CONTRIBUTING.md` | 6 | Must change |
| `config/` | 5 | Check `.env.example` app-name values |
| `AGENT.md` / `SECURITY.md` | 3 | Must change |

Plus the high-visibility strings: `src/frontend/index.html` (3: `<title>`, meta description, apple-mobile-web-app-title), `src/frontend/package.json` (`"name": "healthcentral-frontend"`), `dev.ps1` (5 banner/window-title strings), `dev.bat` (2).

**Explicitly kept (out of scope):** repo directory name (separate optional step), `HC-*` test/ticket prefixes, `HC_*` environment variables, vault/DB filenames (renaming breaks existing vaults), historical `docs/plans/` logs, git history.

Estimated must-change set: ~45 user-visible strings across ~20 files — a one-PR rename.

## Candidate shortlist

Screened = one web-search pass for existing health/software products with that name (2026-07-07). This is a first filter only — stage 2's trademark/domain check is the real clearance.

| Candidate | Screening result | Notes |
|-----------|------------------|-------|
| **LabTrail** | ✅ No collision found | Evokes longitudinal lab trends; pronounceable; no medical-claim implication |
| **ResultKeeper** | ✅ No collision found | Literal, honest (organize + keep results); slightly utilitarian |
| **Trendwell** | ✅ No collision found | Trend focus + wellbeing; slightly generic wellness-brand feel |
| **Labwise** | ✅ No collision found | Short; "wise" mildly implies advice — review against the non-diagnostic boundary |
| **LabLedger** | ⚠️ Weak collisions | A Kindle notebook guide + a scientific peer-review project use the name; no health-app collision |
| Hearthfolio | ◻ Unscreened | Coined; warm/local connotation |
| Labarium | ◻ Unscreened | Coined; distinctive, likely clear |
| Trendfolio | ◻ Unscreened | Coined; trends + portfolio of records |

Ruled out during screening: **LabVault** (existing Houston lab-services company, lab-vault.com), **Vitalog** (existing patient-provider app on both app stores), **Healthfolio** (existing crypto-healthcare payment platform, health-folio.com). Also avoid anything implying diagnosis/treatment ("...Doctor", "...Dx", "...Diagnosis") per the product's safety boundary.

Screening sources: [LabVault](https://lab-vault.com/), [Vitalog (App Store)](https://apps.apple.com/us/app/vitalog/id6502337743), [Healthfolio](https://health-folio.com/), [LabLedger (X)](https://x.com/LabLedger).

## Stage 3 execution (after owner clearance)

1. Change user-visible strings only (table above): frontend `index.html`/branding components, `package.json` name, FastAPI `title=`, dev script banners, README/CONTRIBUTING/AGENT/SECURITY headers, product-presenting docs.
2. Keep internal identifiers (`HC_*`, `HC-*`, DB filenames) — recorded above.
3. Regenerate docs index (`python3 scripts/generate_docs_index.py && python3 scripts/docs_lint.py --link-graph`).
4. Verify: grep for the old name returns only historical logs + kept identifiers; app boots with the new title; `npx tsc --noEmit`, vitest, and docs gates pass.
5. Update `feature_list.json` HC-M10 → completed; record the decision in `docs/agentic/progress.md`.
