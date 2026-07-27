# Sprint 0 — Inception (2026-06-22 → 06-28)

> Historical Reference: this sprint record is retained for history and is not an active tracker; the sprint completed and is not maintained going forward. For active remaining work, use [`docs/features/TASK_LIST.md`](../../features/TASK_LIST.md).

**Last Updated:** 2026-06-24
**Owner:** [Owner]
**Refresh Trigger:** S0 story scope/AC changes, or the foundation contracts move
**Release:** R1 · **Epic:** E1 · **Phase:** [PHASE_0](../prd-phases/PHASE_0_foundation.md)
**Status:** ✅ Done — all four stories delivered (commit 3e63df2). Suite: 24
passed, 18 skipped (remaining skips belong to future sprints).

## Goal
A provable foundation: `modules/agent/` exists and collects, the `agent_enabled`
flag is wired OFF-by-default, the audit-event schema is defined, and the cadence
files are committed.

## Stories (IDs/points 1:1 with AGILE_PLAN §6)
| ID | Story | Acceptance criteria | Pts | Status |
|---|---|---|---|---|
| S0-1 | Scaffold `modules/agent/` | dirs + empty graph runner import-clean; `pytest` collects `tests/agent/` | 2 | ✅ Done (planning bundle) |
| S0-2 | Add `agent_enabled` flag to model settings | flag defaults OFF; `/assistant/` path unchanged when off | 2 | ✅ Done (commit 3e63df2) — see AC deviation note below |
| S0-3 | Define audit-event schema for agent nodes | one event persists through existing monitoring/audit | 3 | ✅ Done (commit 3e63df2) |
| S0-4 | `AGILE_PLAN` + `STANDUP`/`RETRO` under `docs/agile/` | files committed | 1 | ✅ Done (planning bundle) |

### AC deviation note (S0-2)
S0-2's AC is met **functionally**: `is_agent_enabled` defaults OFF
(`AGENT_ENABLED_DEFAULT = False`) and is defensive on shape (`None` / dict /
ORM-attribute access), so `/assistant/` is unchanged when off. However, no
persisted `agent_enabled` column exists yet on `UserModelSettings` (no
migration adds one) — so today the helper can only ever read the absent-key
default. Tracked as a gap, not a blocker for S0 close-out, in
[`RECONCILIATION.md` R-8](../agile/RECONCILIATION.md); recommended resolution is
the S5 cutover sprint (S5-1) adding the column + migration.

## DoR / DoD (AGILE_PLAN §2)
- **DoR:** each story above has AC, a touched-files list (see Phase 0 contracts +
  scaffold paths below), and a proving test in `tests/agent/test_s0_foundation.py`.
- **DoD:** code + test green in CI; audit event emitted for any node/tool added;
  `/assistant/` unchanged when flag off; docs updated; proof bundle passes from the
  WSL interpreter (RECONCILIATION R-2 — re-run on host).

## Test-coverage plan
- **Eval axes:** none yet (no answer path). **Unit suites:** `test_s0_foundation.py`.
- **Targets:** flag-default-OFF assertion (FR-1) ✓ live; audit-schema field
  assertion ✓ live; terminal-schema validates 3 terminals ✓ live; `MAX_STEPS == 5`
  ✓ live. Implementation tests (flag-off no-change regression; audit persistence)
  are skip-marked until S0 lands. Coverage target for new S0 code: **≥ 80%**.

## Code templates (committed scaffolds)
- `modules/agent/__init__.py`, `schemas.py` (`Citation`, `AgentTerminal`),
  `audit.py` (`AgentAuditEvent`, `emit_audit_event`), `settings.py`
  (`AGENT_ENABLED_DEFAULT`, `is_agent_enabled`), `state.py` (`MAX_STEPS`, `RunLog`),
  `graph.py` (`run_agent` stub).
- Tests: `tests/agent/test_s0_foundation.py`, `conftest.py`.

## Standup / retro pointers
- Append the daily one-liner to [`docs/agile/STANDUP.md`](../agile/STANDUP.md) (newest on top).
- Sunday: 3 bullets (keep/drop/try) to [`docs/agile/RETRO.md`](../agile/RETRO.md); re-ask the
  three iteration questions (AGILE_PLAN §8). **Review (client hat):** demo the
  flag-OFF no-change guarantee to yourself before accepting S0-1/S0-2.
