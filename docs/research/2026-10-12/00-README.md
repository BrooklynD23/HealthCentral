# Wearable evidence integration — feasibility package (2026-10-12)

> **Point-in-time research (2026-10-12).** Planning and documentation only. No
> product code changed. Code facts verified on `origin/main@4884d38` in worktree
> `docs/wearable-feasibility`. Vendor facts carry their own source URL and an
> access date of 2026-10-12. Decisions are listed in
> [06-decisions-go-nogo.md](06-decisions-go-nogo.md). Owner direction of
> 2026-10-13 (rows WEAR-OD1, WEAR-OD2, WEAR-PR) is applied below; every other
> decision stays open until the owner answers it.

## Owner direction applied (2026-10-13)

Quoted verbatim from the owner-decisions rows held by L0:

- **WEAR-OD1:** "Since this project is a research study, can we disclaimer to
  not use it as professional medical/legal advice. It's about open-sourcing and
  allowing for development for those who are curious about their healths to
  track it in a centralized way & develop personal software to track and make
  use of their health/fitness recording. As I only have Apple & Garmin watch,
  can we focus on getting the datas from those to be fully-integrated into
  HealthCentral? The original prompt ask for multi-repo setup with wearable as
  additional plugin (would multi-repo works, or a single-repo?)"
- **WEAR-OD2:** "Refer to first question's answer for me. If it works better
  internally within this repo, then in-repo"
- **WEAR-PR:** "Yes, docs PR (Recommended)"

What changed in this package as a result:

1. **Scope:** Apple Watch (Apple Health "Export All Health Data" ZIP) and
   Garmin (Garmin Connect "Export Your Data" / FIT files) only. Samsung is
   **out of scope (owner has no device)**; its findings are retained for
   reference and not acted on.
2. **Framing:** an open-source, personal, research and educational tool for
   individuals curious about their own health and fitness records. It is not
   professional medical or legal advice. Whether it is a medical device is
   not settled here: that stays with OD-8 / OM-7 / OM-8 (corrected after
   Codex review 2026-10-13, see [response](../../reviews/2026-10-13/WEAR-RESEARCH-response.md), finding C3). The framing
   **relaxes no control**: every safety, privacy, provenance, redaction,
   profile-isolation and no-medical-advice control in
   [03](03-architecture-contracts.md) and [04](04-safety-privacy.md) stays.
3. **Repository:** single repo, in-repo module behind a default-off flag
   (see [Single repo or multi-repo](#single-repo-or-multi-repo)).
4. **Decisions:** OD-1 and OD-2 resolved by WEAR-OD1/WEAR-OD2; OD-3..OD-8 stay
   open ([06](06-decisions-go-nogo.md)).

## Executive verdict

**Technically feasible; pursued by owner direction (WEAR-OD1), gated on real
export files.** A file-based, descriptive-statistics slice — Apple first,
Garmin second — fits the existing structured-import and visit-prep paths
without a mobile app, live sync, vendor cloud API, or a model. Before any code:
(1) a real Apple export (OM-1) inspected end to end before the Apple slice, and
a real Garmin export (OM-2) before the Garmin slice (corrected after Codex review 2026-10-13, see [response](../../reviews/2026-10-13/WEAR-RESEARCH-response.md), finding C4). Whether (2) direct patient or clinician demand (OM-4/OM-5) is still
required under the personal open-source framing is **open — owner to
confirm**. The 2026-07-10 roadmap deferral of wearables is superseded for this
scope by WEAR-OD1.

## Recommendation

**Build in HealthCentral, in-repo, behind a default-off `wearables_enabled`
flag (WEAR-OD2). Apple slice first, then Garmin. Do not start a separate plugin
repository. Write no code until OM-1 (Apple export) — and, for the Garmin
slice, OM-2 (Garmin export) — are done and OD-3, OD-4, OD-6 are signed.**

| Option | Verdict | Why |
|---|---|---|
| In HealthCentral | **Chosen (WEAR-OD2), after OM-1/OM-2** | Every safety property needed (vault encryption, `ProfileDbSession`, redaction, audit, HTTP route tests) already lives here. The parser can follow the pure-module contract of `modules/import_structured.py`, so moving it out later stays cheap. |
| Separate plugin repo | **Not now** | HealthCentral has no plugin or extension mechanism (no entry points, no loader). The only zero-change seam, a FHIR Bundle converter, loses device, time-of-day and offset, and lands daily aggregates in the lab paths ([03](03-architecture-contracts.md#5-separate-repository-option)). A proper seam needs a new versioned contract **inside** HealthCentral first, so a plugin is strictly more work than in-repo. |
| Defer | **Superseded by WEAR-OD1** | Was recommended on 2026-10-12 (no recorded demand; 2026-07-10 roadmap deferred wearables; vendor format facts unverified). The export-format facts are still unverified, which is why OM-1/OM-2 gate the code. |

### Verified, inferred, assumed

| Class | Claims |
|---|---|
| **Verified** (code read or command run here; or vendor page read) | Structured import exists and is pure stdlib (`modules/import_structured.py:1-23`). Imported rows are always `user_verified=False` (`api/documents.py:759`). `Observation.doc_id` is NOT NULL and `Observation` has no device or provenance fields (`models/observation.py:47-52`). The FHIR date parser drops time and offset: `_parse_date('2026-10-01T23:30:00-07:00')` returns `'2026-10-01'` (run 2026-10-12). Visit-prep is redacted at strict before storage (`modules/export.py:502-675`). No symptom model exists (grep of `models/`, `api/` for "symptom" returns nothing). Health Connect reads default to 30 days back without `PERMISSION_READ_HEALTH_DATA_HISTORY` (developer.android.com, read). HealthKit is on-device Swift/Obj-C only, read-only for ECG (developer.apple.com, read). Garmin Health API is approval-gated with a commercial fee (developer.garmin.com, read). Garmin states Pulse Ox is "not considered a medical device" (garmin.com, read). |
| **Reasonable inference** | Apple's export ZIP holds `export.xml`, `export_cda.xml`, `electrocardiograms/*.csv`, `workout-routes/*.gpx` (several consistent third-party sources; Apple support page did not render). Descriptive, non-alerting summaries stay inside FDA general-wellness policy (secondary summaries of the January 2026 guidance). A daily-aggregate table is safer than raw samples or `Observation` rows. |
| **Untested assumption** | Patients will export and move a 100 MB+ file. Clinicians will read a wearable section. The packet adds signal, not noise. Samsung export is CSV with a `time_offset` column (out of scope, reference only). Garmin wellness JSON holds stress, HRV, SpO2. |

## Single repo or multi-repo

**Answer: single repo.** The wearable importer is an in-repo module in
HealthCentral behind `wearables_enabled: bool = False` in `core/config.py`.
Multi-repo would work only after extra work inside HealthCentral, costs more,
and gains no safety. Reasons (evidence in [02 §6](02-implementation-map.md#6-extension-points-for-an-external-module)
and [03 §5](03-architecture-contracts.md#5-separate-repository-option)):

1. **No plugin mechanism exists.** No entry points, no loader, a static router
   mount list (verified, grep of product code).
2. **A separate repo first needs a versioned import contract inside
   HealthCentral.** The only zero-change seams (FHIR Bundle, lab CSV) are
   unsafe: they drop device, time and offset and land data in the lab paths.
   HealthCentral would still have to build the importer, table, review,
   packet section and safety tests itself.
3. **More cost, no safety gain.** A plugin adds a second repo, releases, a JSON
   Schema, cross-repo version tests and a patient converter step. Every safety
   property (vault encryption, `ProfileDbSession`, redaction, audit, HTTP route
   tests) stays in HealthCentral either way.

**What would make a later extraction into a plugin repo cheap** (described,
not built): a clean internal seam — the vendor parsers stay pure modules that
import nothing from HealthCentral but the stdlib, and emit the
`wearable-summary` v1 row shape ([03 §5.2](03-architecture-contracts.md#52-seam-a-plugin-would-need));
the importer validates that shape before storage. Revisit extraction only if a
second independent consumer of the parsers appears, or the FIT licence (OM-7)
requires keeping the Garmin parser out of the main distribution.

## Package contents

| # | File | Deliverable |
|---|---|---|
| 1 | this file | Executive verdict, recommendation |
| 2 | [01-vendor-matrix.md](01-vendor-matrix.md) | Vendor/API capability and licensing matrix |
| 3 | [02-implementation-map.md](02-implementation-map.md) | Existing implementation map with file-level evidence |
| 4 | [03-architecture-contracts.md](03-architecture-contracts.md) | Proposed architecture, data contracts, separate-repo seam |
| 5 | [04-safety-privacy.md](04-safety-privacy.md) | Privacy, security, clinical-safety assessment; failure modes and controls |
| 6 | [05-mvp-roadmap-tests.md](05-mvp-roadmap-tests.md) | Minimum vertical slice, roadmap, acceptance tests, validation study |
| 7 | [06-decisions-go-nogo.md](06-decisions-go-nogo.md) | Unresolved questions, owner decisions, go/no-go, owner and model-machine tasks |

## Why `docs/research/<date>/`

The repo has two dated conventions. `docs/plans/YYYY-MM-DD-*.md` holds single
plans and decision records that license or gate work
(e.g. [2026-10-01-packaging-decision.md](../../plans/2026-10-01-packaging-decision.md)).
`docs/research/YYYY-MM-DD/` holds multi-track research packages with a brief
and numbered tracks ([2026-09-08](../2026-09-08/00-brief.md)). This is a
multi-track research package that licenses no code, so it follows the second.
A `docs/plans/` decision record is the right follow-up only if the owner
passes the go gate.

## Method

Six read-only workstreams ran in parallel: A Apple, B Garmin, C Samsung/Android
(now reference only),
E clinical safety, F demand (web, Haiku), D code map (Haiku). Their reports
were treated as leads. Code claims above were re-read by the orchestrator; two
vendor claims were re-fetched (Health Connect 30-day limit, Apple export layout
search). Claims not re-checked keep the label the workstream gave them.

## Out of scope

Samsung and Android Health Connect (owner has no device; findings retained for
reference), live sync, mobile apps, vendor cloud APIs (including the Garmin
Health API), ECG waveform analysis, any ML inference, any alerting. Edits to ask-first files (`modules/interpret_safety.py`,
`modules/redaction.py`, `modules/faithfulness.py`, `modules/verifier_agent.py`,
auth/encryption) are neither made nor proposed; the design only **calls**
`modules/redaction.py` the way `modules/export.py` already does.
