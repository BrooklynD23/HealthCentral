# WEAR-PLANS D1-D8 — response to the Opus reviews (substituting for Codex per owner instruction 2026-10-14)

**Reviews:** [Opus review](WEAR-PLANS-D1D8-opus-review.md) — needs-attention, 1 P1, 6 P2, 4 P3 (R1-R11). [Opus adversarial](WEAR-PLANS-D1D8-opus-adversarial.md) — needs-attention, 1 BLOCKER, 2 HIGH, 6 MEDIUM, 2 LOW (A1-A11). Neither is a Codex review. The Codex r3 runs on `ad8e191` completed and are recorded separately ([WEAR-PLANS-r3-codex.md](WEAR-PLANS-r3-codex.md)).
**Responder:** Wearables Planning Sub-Orchestrator (Opus 5.5), 2026-10-14. Findings were checked against the plan text and the cited lines; fixes applied after this round are not re-reviewed.

| # | Finding | Sev | Disposition |
|---|---|---|---|
| R1 / A2 | Plan 15 contradicts its own §0 on `core/audit.py` | P1 / HIGH | **ACCEPTED.** All 7 sites rewritten to §0. HC-WRB-1512 asserts `row.action in ALLOWED_ACTIONS`. Task 2 adds the vocabulary and the HC-AUD-004 extension. The diff checks expect exactly the OW-W11 lines. |
| A1 / R3 | OW-W9 gate exists only in prose | BLOCKER / P2 | **ACCEPTED.** WEAR-09 is split into 09a-metrics (does not wait) and 09a-journal (Task 0 STOP on the OW-W9 row). 09b is split the same way. Each part has its own tests and count. Tickets and program updated. |
| R2 | HC-WRB-925 expects 404 where the check order gives 400 | P2 | **ACCEPTED.** Packet → 400 (C27); 404 is asserted on the preview route; check order stated. |
| R4 | WEAR-D7 opt-in has no UI path, so the patient's normal export lacks wearable rows | P2 | **ACCEPTED.** WEAR-13 adds a small frontend change: `services/export.ts` sends `include_wearables=true` when the feature is on. The opt-in follow-up is removed. |
| R5 | Program A10/R6/A5b still describe the rejected D6 default | P2 | **ACCEPTED.** Rewritten to the signed WEAR-D6 (b) design. |
| R6 / A7 | Plan 11: stale JSON-only text, wrong count, no 11b tasks, 1104 conflict | P2 / MEDIUM | **ACCEPTED.** Retitled. Count fixed. 11b task block added: licence row, exact pin, pure-python 3.11 wheel, zero transitive deps, wheel sha256, CI install. 1104 re-scoped. |
| R7 | Plan 14 still says D7 (b); TASK_LIST covers only OW-W0..W6; deps stale | P2 | **ACCEPTED.** D7 (a); OW-W0..W13; deps 06, 09a-metrics, 13, 15a. |
| R8 | "Confirmation" remnants after the switch to `preview_id` | P3 | **ACCEPTED.** |
| R9 | 15b mounts into a placeholder 07b already removed | P3 | **ACCEPTED.** Journal mounts after the 07b/08b sections. |
| R10 | HC-WRB-931 calls a route its test client does not mount | P3 | **ACCEPTED.** The test edits and deletes the row directly in the profile DB. |
| R11 | Stale D6 wording, garbled ", ;", OW-W4 suites | P3 | **ACCEPTED.** |
| A3 | Deleted journal text survives in generated packets (and in G-C1 persisted packets) | HIGH | **ACCEPTED.** Plan 15 states the gap. Journal PUT/DELETE drop preview snapshots holding that id (tested). G-C1 is added as a refresh trigger. J11 is reworded ("Packets you already generated keep their copy."), still OW-W8. |
| A4 | `_journal_preview_store` unbounded, not single-use, not purged | MEDIUM | **ACCEPTED.** Expired snapshots are purged on insert. Cap is 5 per profile. A snapshot is popped on success and purged on profile reset/delete. Editing the reset/delete paths follows the RL-EXPORTS-DELETE-PATH precedent, so it is owner-gated: new **OW-W12**. |
| A5 | Audit tests patch the logger; preview may return text after a failed audit; action string | MEDIUM | **PARTIALLY ACCEPTED.** Tests now use a real master DB and assert persisted keys. A failing `audit_and_commit` → 500 with no text. Not accepted: a new action string. The preview keeps `log_export_event` ("Exported data", already registered): redacted patient text does leave the server to the client, and a new string would be another `core/audit.py` diff. |
| A6 | No packet test pins the 14-day threshold | MEDIUM | **ACCEPTED.** Pure 13/14 boundary test plus an HTTP 13-day test in 09a-metrics. |
| A8 | Socket patch does not prove the FIT parser stays offline; weak supply chain | MEDIUM | **ACCEPTED.** Module imported inside the patch; `getaddrinfo` and `subprocess.Popen` patched; static scan of the installed package (HC-WRB-1121); wheel sha256 and zero transitive deps recorded. |
| A9 | Migration numbers collide with other plans; no single-head test | MEDIUM | **ACCEPTED.** Program A11 adds a migration ledger (recommended order P6 → G-C1 → AUDIT-ORDER → GAM2-2b → WEAR-02 → WEAR-15; the later lander renumbers). New owner item **OW-W13** confirms the order. WEAR-02/15 add a single-Alembic-head test. The 1501 downgrade target is read from the migration file. |
| A10 | Delete-after-preview untested | LOW | **ACCEPTED.** Added to 931. |
| A11 | Copy J3 can be false when 15b ships | LOW | **ACCEPTED.** Second sentence dropped until 09b-journal. |

**Totals:** 22 findings, 21 accepted, 1 partially accepted, 0 declined. New owner items: OW-W12 (snapshot purge in the profile reset/delete paths) and OW-W13 (profile-migration merge order).
