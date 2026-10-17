# WEAR-PLANS r1 — response to the Codex review of the plan set

**Review:** [WEAR-PLANS-r1-codex.md](WEAR-PLANS-r1-codex.md) — native review 5 × P2; adversarial **needs-attention** (2 high, 3 medium).
**Responder:** Wearables Planning Sub-Orchestrator (Opus 5.5), 2026-10-13. Each finding checked against the plan text and the tree at `8234990`.

| # | Finding | Sev | Disposition | Change |
|---|---|---|---|---|
| N1 | Exact duplicate step records would be summed | P2 | **ACCEPTED.** Exact duplicates (same source, start, end, value) collapse to one; skip reason `duplicate_record`; HC-WRB-518; OM-1 checks whether they occur. | WEAR-05 contract row; program OW-W0 |
| N2 | Garmin parser materialises all records and whole JSON members | P2 | **ACCEPTED.** Records are yielded; per-member JSON byte cap before `json.loads`; memory test at production defaults (HC-WRB-1117). | WEAR-11 §6 |
| N3 | Upload copy stays Apple-only when Garmin ships | P2 | **ACCEPTED.** WEAR-07b R2/R8 are vendor-neutral from the start; WEAR-12 only flips `GARMIN_EXPORT_READY`. | WEAR-07b, WEAR-12 |
| N4 | Research lead-in "Before any code:" still reads as a blanket gate | P2 | **ACCEPTED, research corrected** ("Before each slice's code:") in a separate labelled commit. Factually inconsistent with 05/06, same class as research finding C4. | `docs/research/2026-10-12/00-README.md` |
| N5 | "Processed on this computer" is false with a remote `VITE_API_URL` | P2 | **ACCEPTED.** Copy now says "processed by your HealthCentral app" and "sends nothing to Apple, Garmin or any other online service" — true in any configuration. | WEAR-10 C6, C7 |
| ADV-1 | Symptom notes leak natural-language names past strict redaction | high | **ACCEPTED.** D2 default changed from (a) to (c) none; notes are built only if the owner signs (a) accepting the exposure (same as `reason_for_visit` today). `modules/redaction.py` stays untouched (ask-first). | Program D2; WEAR-09 scope and §12; tickets |
| ADV-2 | Parser limits do not bound memory/metadata | high | **ACCEPTED.** Central-directory size cap read from EOCD before `ZipFile`; placeholder caps replaced at Task 0 from OM-1 sizes; memory test at production defaults (HC-WRB-423); parse time on multi-GB exports stays OW-W2. Garmin JSON cap under N2. | WEAR-04 caps table; WEAR-11 |
| ADV-3 | Program A5b still says `upload.file` + `seek(0)` | medium | **ACCEPTED.** A5b now states the raw-body, stream-to-temp contract. | Program A5b |
| ADV-4 | Audit holds `import_id` and `vendor`, not counts only | medium | **PARTIALLY ACCEPTED.** Kept: `import_id` is an opaque UUID, logged the same way `document_id` is for documents today, and is needed to tie review/delete rows to their import; `vendor` is a 2-value enum. The wording was wrong: program M2 and WEAR-14 now say "counts plus opaque `import_id` and `vendor` enum; never filenames, device names, values or dates". | Program M2; WEAR-14 |
| ADV-5 | Concurrent duplicate upload returns 500 | medium | **ACCEPTED.** `IntegrityError` on the unique hash → rollback, re-read, 409; concurrent test HC-WRB-620. | WEAR-06 Task 2 |

**Totals:** 10 findings — 9 accepted, 1 partially accepted, 0 declined. Two high findings accepted, so round 2 runs once (program rule).
