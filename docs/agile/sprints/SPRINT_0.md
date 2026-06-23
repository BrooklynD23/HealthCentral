# Sprint 0 — Inception (2026-06-22 → 06-28)

**Last Updated:** 2026-06-23
**Owner:** [Owner]
**Refresh Trigger:** S0 story scope/AC changes, or the foundation contracts move
**Release:** R1 · **Epic:** E1 · **Phase:** [PHASE_0](../../prd/phases/PHASE_0_foundation.md)

## Goal
A provable foundation: `modules/agent/` exists and collects, the `agent_enabled`
flag is wired OFF-by-default, the audit-event schema is defined, and the cadence
files are committed.

## Stories (IDs/points 1:1 with AGILE_PLAN §6)
| ID | Story | Acceptance criteria | Pts |
|---|---|---|---|
| S0-1 | Scaffold `modules/agent/` | dirs + empty graph runner import-clean; `pytest` collects `tests/agent/` | 2 |
| S0-2 | Add `agent_enabled` flag to model settings | flag defaults OFF; `/assistant/` path unchanged when off | 2 |
| S0-3 | Define audit-event schema for agent nodes | one event persists through existing monitoring/audit | 3 |
| S0-4 | `AGILE_PLAN` + `STANDUP`/`RETRO` under `docs/agile/` | files committed | 1 |

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
- Append the daily one-liner to [`docs/agile/STANDUP.md`](../STANDUP.md) (newest on top).
- Sunday: 3 bullets (keep/drop/try) to [`docs/agile/RETRO.md`](../RETRO.md); re-ask the
  three iteration questions (AGILE_PLAN §8). **Review (client hat):** demo the
  flag-OFF no-change guarantee to yourself before accepting S0-1/S0-2.
