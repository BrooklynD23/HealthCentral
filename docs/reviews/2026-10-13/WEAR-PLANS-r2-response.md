# WEAR-PLANS r2 — response to the Codex round-2 review

**Review:** [WEAR-PLANS-r2-codex.md](WEAR-PLANS-r2-codex.md) — **needs-attention**, 2 high, 4 medium. Five of the six are r1 fixes that were stated in prose but not carried into the test tables, counts or every copy row; one is a minimisation gap.
**Responder:** Wearables Planning Sub-Orchestrator (Opus 5.5), 2026-10-13.
**Round cap:** this is round 2, the last one allowed per amendment (`docs/agentic/orchestration.md` §5). The fixes below were applied after r2 and are **not re-reviewed**; the owner may ask for a round 3.

| # | Finding | Sev | Disposition | Change |
|---|---|---|---|---|
| R2-1 | WEAR-09 header still says D2 default (a); notes can leak names | high | **ACCEPTED.** Header now states D2 default (c), notes built only on a written D2 (a); a name-capable sanitizer would touch ask-first `modules/redaction.py` and is its own owner decision. | WEAR-09 header, status |
| R2-2 | C2 "kept on this computer" and C7 still deny the upload | high | **ACCEPTED.** C2: "kept in your HealthCentral data". C7 now discloses the upload to the connected HealthCentral backend (standard setup: this computer) and says HealthCentral sends nothing to Apple, Garmin or other online services. | WEAR-10 C2, C7 |
| R2-3 | HC-WRB-620 race test referenced but not in the table/count | medium | **ACCEPTED.** Row added (Barrier-synchronised pair → exactly {201, 409}); count 19 → 20; WEAR-06 summary audit wording aligned. | WEAR-06 |
| R2-4 | HC-WRB-1117 Garmin memory test missing from table/count | medium | **ACCEPTED.** Row added (production default caps, tracemalloc ceiling); count 16 → 17. | WEAR-11 |
| R2-5 | HC-WRB-518 duplicate-step test missing from table/count | medium | **ACCEPTED.** Row added; count 17 → 18. Same gap found and fixed for HC-WRB-423 in WEAR-04 (count 22 → 23). | WEAR-05, WEAR-04 |
| R2-6 | `metric` in audit details exceeds the minimisation contract | medium | **ACCEPTED.** `metric` is no longer reserved as a string key; HC-WRB-212 now asserts it is dropped; WEAR-07 details list and program A12 updated. Counts `metrics_reviewed` / `metrics_included` stay. | WEAR-02, WEAR-07, program A12 |

**Totals:** 6 findings, 6 accepted, 0 declined.
