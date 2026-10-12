# AUDIT-ORDER — security review response

**Last Updated:** 2026-10-09
**Plan:** `docs/plans/2026-10-09-AUDIT-ORDER.md` (PR #56), reviewed at `d696c5d`, base `origin/main` `98bd3c7`.
**Reviewer:** security-reviewer (opus), dispatched by L0. Verdict line as relayed by L0: "VERDICT CHANGES, 2 HIGH, 4 MEDIUM, 4 LOW". The full review text is not in a file; this response works from L0's message, which listed 6 must-fix items and 5 later items.
**Result:** 11 of 11 accepted after checking against the code at `98bd3c7`. 9 are fixed in the plan text; 2 are fixed and also listed in §12 (Residual review risk). None rejected.

## Must fix

| # | Sev | Finding | Verified at `98bd3c7` | Disposition |
|---|---|---|---|---|
| 1 | HIGH | A D-B denial row that is only added before the raise is lost | `core/database.py:117-119` rolls back on any exception, `HTTPException` included; `require_profile_access` has no DB session (`core/auth.py:264-267`) | **Accepted, fixed.** Plan: "Commit before the raise" (`audit_and_commit` in the export handlers; its own committed master session in `require_profile_access`). HC-AUD-ORD-040 runs with a `get_db` override that reproduces commit-on-exit and rollback-on-exception; break-it: drop the commit → test fails |
| 2 | HIGH | The UUID-only `entity_id` rule would null legitimate values | `backup.py:231`, `:514` (`"all"`); `:272` (`backup_YYYYMMDD_HHMMSS`, built at `scripts/backup.py:310-311`); `:301`, `:459`, `:487` (`backup_id`); `:564` (`"schedule"`); also `search.py:113`, `timeline.py:104` (`"all"`) | **Accepted, fixed.** Rule is now: UUID, or matches `_ENUM_VALUE_RE` and ≤ 36 chars. HC-AUD-ORD-006 has survival cases for `backup_…`, `all` and `schedule`. The plan lists every audit `entity_id=` caller grouped by shape (Citation `entity_id` at `assistant.py:647`, `:1269` and `query_medication_changes.py:89` excluded: those are not audit rows) |
| 3 | MEDIUM | Row 27: a `completed` row would carry the deleted profile id | `profiles.py:927-936` already writes a tombstone with `profile_id=None`, `entity_id=None` | **Accepted, fixed.** The tombstone is the completion marker; no `completed` row. HC-AUD-ORD-007: after delete, the target id appears in no `audit_logs` column or detail |
| 4 | MEDIUM | Export denial rows keep the artifact id, which joins to the victim's `export.create` row | export stores keyed by artifact id (`export.py:498`, `:840`, `:1267`) | **Accepted, fixed.** `entity_id=None` for export denials, `entity_type` kept. HC-AUD-ORD-042 now also asserts no join to `export.create` |
| 5 | MEDIUM | The denial cap was unspecified | the rate limiter keys by client IP (`security/rate_limit_middleware.py:81-97`), so on a local app it is one global bucket | **Accepted, fixed.** 20 rows per caller `profile_id` per rolling 10 minutes, then one `denial.suppressed` row with `count`; HC-AUD-ORD-041 tests the suppression row. Residual: the counter is in-process and resets on restart (§12 item 8) |
| 6 | MEDIUM | AO-FAIL must say that option A blocks erasure | erase already needs a master commit (`profiles.py:936`) | **Accepted, fixed.** AO-FAIL option A now says plainly that a master-DB fault blocks profile erase (right to erasure), and that this keeps an existing dependency rather than adding one |

## Later

| # | Finding | Disposition |
|---|---|---|
| 7 | HC-AUD-ORD-030 cannot see writes that rely on the vault exit commit (`core/profile_database.py:80`) | **Fixed in text** (the guard flags vault writes with no reachable commit) **and listed** as §12 item 7 (static-analysis limit) |
| 8 | A2 should apply per branch on rows 10 and 19/20/23 | **Fixed in text.** Option D scope: `hard_delete` (`medications.py:648-650`) and `force_regenerate` with an existing interpretation (`modules/interpret.py:272-276`) only; pin pruning (`pinboards.py:202`) for rows 29/30 |
| 9 | The relay matches on primary-key conflict alone | **Fixed in text.** A conflict counts as relayed only if `event_type`, `entity_type`, `entity_id` and `profile_id` match; a mismatch logs ERROR and stops. Listed in §12 item 5 as not re-reviewed |
| 10 | Under D-B, drop the target id from the WARNING at `core/auth.py:279-282` | **Fixed in text.** D-B's edit list now includes it |
| 11 | Export 403-vs-404 reveals that an artifact exists | **Listed** as §12 item 6, an accepted residual (`export.py:500-511`, `:841-851`, `:1268-1278`; ids are UUID4) |

No safety check, threshold or validation is weakened. No file under `src/` was edited.
