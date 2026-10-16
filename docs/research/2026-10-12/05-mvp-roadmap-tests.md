# 05 — Minimum vertical slice, roadmap, acceptance tests, validation study

> **Point-in-time research (2026-10-12).** Nothing here is licensed until the
> go gate in [06](06-decisions-go-nogo.md) passes. Back to
> [00-README.md](00-README.md). Owner direction 2026-10-13: Apple and Garmin
> in scope (WEAR-OD1), built in-repo behind a default-off flag (WEAR-OD2).

## 1. Minimum credible MVP

**Source (slice 1):** Apple Health "Export All Health Data" ZIP only. Garmin
follows as slice 2 (roadmap item 10).
**Metrics:** resting heart rate, sleep duration (asleep minutes), steps.
**Window:** patient picks up to 90 days before the visit.

| Step | Patient sees | System does | Reuses |
|---|---|---|---|
| 1 Export | Instructions page: how to export on iPhone and copy the ZIP | — | — |
| 2 Import | Upload in Document Inbox | Vault-encrypt, hash, detect `wearable_apple_export`, stream-parse allowlist, write `wearable_daily_metrics` | `POST /documents/import`, structured-import dispatch |
| 3 Review | Per metric: days with data, median/IQR, source device, skipped counts; toggle "include in packet" | Sets `patient_reviewed_at`, `include_in_packet`; audit | Verification-first pattern |
| 4 Trends | "Wearable (patient-recorded)" panel, daily median with IQR band, table twin | Read-only from new table | Recharts |
| 5 Symptom context | Up to 5 dated notes typed on the visit-prep form | Printed beside the metric table for the same dates; no linkage claim | `reason_for_visit` precedent |
| 6 Packet | New optional section in visit-prep | Template render → strict redaction → `confirm=true` → audit | `compose_visit_prep_packet` |

**Explicitly excluded:** live sync, mobile app, Samsung (out of scope),
Garmin until slice 2, SpO₂, HRV,
stress, ECG analysis, any LLM text, any threshold or "normal range".

**Size estimate (INFERRED):** one parser module, one model + migration
`013_*`, one review route, one packet section, two frontend surfaces. Roughly
the size of HC-M23 plus HC-M18's section work.

## 2. Dependency-ordered roadmap

| # | Item | Depends on | Gate |
|---|---|---|---|
| 0 | Evidence gate: OM-1 (and OM-2 before item 10), OM-6 in [06](06-decisions-go-nogo.md); OM-4/OM-5 open — owner to confirm whether still required | — | Go/no-go signed |
| 1 | Decision record in `docs/plans/` turning this package into tasks | 0 | Owner signs OD-3..OD-8 (OD-1, OD-2 resolved by WEAR-OD1/WEAR-OD2) |
| 2 | Synthetic Apple export fixtures (from OM-1 real-file structure, no real data) | 1 | Fixtures reviewed |
| 3 | `modules/import_wearable.py` pure parser + hostile-file tests (F3-F6, F12-F13) | 2 | Tests red→green |
| 4 | `wearable_daily_metrics` model + profile migration `013_*` + `wearables_enabled` flag | 1 | Migration up/down test |
| 5 | Import dispatch + size/extension changes + audit keys | 3, 4 | HTTP tests via `route_client` (F9, F14) |
| 6 | Review route + review screen | 5 | F8, F10 |
| 7 | Trends panel | 6 | a11y test |
| 8 | Visit-prep section + symptom notes | 6 | F1, F2, F7, F8, F11 |
| 9 | Patient CSV export of wearable rows | 4 | Schema-version test |
| 10 | Garmin slice: Garmin Connect export parser (pure), `source_vendor = garmin`, same table, review, packet and tests as items 3-9 | 3-9, OM-2 | Hostile-file and HTTP tests red→green; FIT licence read (OM-7) before any distribution |
| 11 | Validation study (§4), only if OM-4/OM-5 are confirmed still required | 8 | Study criteria met |

Steps 3 and 4 can run in parallel. Steps 2-9 need no model-capable machine
(no LLM in the slice). Real-file checks need the owner's phone.

## 3. Acceptance tests

| ID (proposed) | Assertion |
|---|---|
| HC-WRB-001 | Parser on synthetic export yields exactly the expected daily rows for 3 metrics; unknown types counted as skipped |
| HC-WRB-002 | Records with different offsets bucket to their own local dates; DST day sets `tz_changed` |
| HC-WRB-003 | iPhone + Watch steps on the same day produce one row from the preferred source |
| HC-WRB-004 | Re-import of the same file leaves row count unchanged and warns on `content_hash` |
| HC-WRB-005 | Entity-expansion XML and zip-bomb fixtures return 400 within a memory cap |
| HC-WRB-006 | `export_cda.xml`, GPX, SpO₂, ECG CSV contents produce zero stored rows |
| HC-WRB-007 | `POST /documents/import` with flag off rejects the ZIP (400) |
| HC-WRB-008 | HTTP: profile B cannot read profile A's wearable rows or include them in a packet |
| HC-WRB-009 | Packet omits metrics not reviewed or not included |
| HC-WRB-010 | Packet section contains median, IQR, n, days-with-data, device, and the "not a clinical measurement" line; contains none of the banned phrases |
| HC-WRB-011 | Packet generation makes no ModelRunner call |
| HC-WRB-012 | `source_name` containing a personal name is redacted in the packet |
| HC-WRB-013 | Metric with fewer than the minimum days is suppressed with a reason |
| HC-WRB-014 | Import, review and packet each write one audit row with counts only |
| HC-WRB-015 | Backend collected-test count rises by exactly the new tests; existing `interpret_safety` and redaction suites unchanged and passing |

Definition of done stays [AGENT.md](../../../AGENT.md#definition-of-done):
outputs seen, not asserted.

## 4. Real-world validation study (no clinical-utility claim before it)

> **Status: open — owner to confirm whether still required under the personal
> open-source framing (WEAR-OD1).** Whatever the answer, the package makes no
> clinical-utility claim without it.

**Design.** Within-subject comparison, 10-15 patients who already own an
Apple Watch and have an upcoming routine visit, and their 5-8 clinicians.
Arm A: standard visit-prep packet. Arm B: same packet + wearable section.
Order counterbalanced on two mock or real visits, or clinicians rate both
versions of the same patient's packet.

| Dimension | Measure | Success threshold (proposed, owner to set) |
|---|---|---|
| Clarity | Clinician: "I understood every line" (5-point) | median ≥ 4 |
| Relevance | Clinician marks each wearable line useful / neutral / noise | ≥ 50% useful, ≤ 20% noise |
| Provenance | Clinician can say which device and how many days (yes/no) | ≥ 90% yes |
| Length | Clinician reading time for section | ≤ 60 s |
| Patient burden | Time from "start export" to packet; dropout | median ≤ 20 min; ≤ 25% abandon |
| Clinician usability | SUS on review screen (patients) | ≥ 68 |
| Net effect | Clinician: "the section changed nothing / helped / distracted" | helped > distracted |
| Safety | Any reader infers a diagnosis or causal claim from the section | zero instances |

**Stop rule.** If noise > useful or any safety instance, stop; do not extend the
packet section further. Distinguish what the study measures (perceived usefulness)
from clinical utility (outcomes), which it does not measure.
