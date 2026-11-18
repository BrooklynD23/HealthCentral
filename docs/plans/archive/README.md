# Archived Off-Repo Plans (2026-11-16)

**Last Updated:** 2026-11-16 (docs batch BATCH-1116A, owner answer OFFREPO-ARCHIVE)

These files are local working notes (plans, diagnoses, owner-gate write-ups, handoffs) that the build program kept
outside the repo under `~/hc-quiet-logs/`. Many docs and `queue.md` rows cite them by that path. They were copied here on
2026-11-16 so a reviewer on `origin/main` can read them.

- Snapshots, not maintained. They are frozen at the copy date and are not updated when the work moves on.
- On any conflict, the hand-maintained docs win (`CLAUDE.md`, `AGENT.md`, `docs/plans/2026-10-15-build-program/queue.md`,
  `docs/capstone-report/owner-decisions-2026-09-27.md`).
- Personal details were removed before copying. Home paths became `~/`, e-mail addresses in commit trailers and
  claude.ai document or artifact IDs became `[redacted]`.
- Raw logs, run data, scripts, model files and the owner-answers file stay local and are not archived.

## Path map

Use this to resolve an old `~/hc-quiet-logs/...` reference to its archived copy.

| Original path under `~/hc-quiet-logs/` | Archived copy |
|---|---|
| `HUMAN-BLOCKERS.md` | [HUMAN-BLOCKERS.md](HUMAN-BLOCKERS.md) |
| `plans-1112/agentic-eval-plan.md` | [plans-1112/agentic-eval-plan.md](plans-1112/agentic-eval-plan.md) |
| `plans-1112/planner-summary.md` | [plans-1112/planner-summary.md](plans-1112/planner-summary.md) |
| `plans-1113/sqlcipher-wheel-plan.md` | [plans-1113/sqlcipher-wheel-plan.md](plans-1113/sqlcipher-wheel-plan.md) |
| `plans-1114/rows-1114-plan.md` | [plans-1114/rows-1114-plan.md](plans-1114/rows-1114-plan.md) |
| `staging-1111a/uidoc006a-diagnosis.md` | [staging-1111a/uidoc006a-diagnosis.md](staging-1111a/uidoc006a-diagnosis.md) |
| `staging-1111c/meds-g-diagnosis.md` | [staging-1111c/meds-g-diagnosis.md](staging-1111c/meds-g-diagnosis.md) |
| `staging-1111i/owner-gates-1111i.md` | [staging-1111i/owner-gates-1111i.md](staging-1111i/owner-gates-1111i.md) |
| `stillness-nav-late/RESULT.md` | [stillness-nav-late/RESULT.md](stillness-nav-late/RESULT.md) |
| `stillness-nav-late-1107-result.md` | [stillness-nav-late-1107-result.md](stillness-nav-late-1107-result.md) |
| `uig006-pass3/RESULT.md` | [uig006-pass3/RESULT.md](uig006-pass3/RESULT.md) |
| `senior-report-doc/HANDOFF-SENIOR-REPORT-DOC.md` | [senior-report-doc/HANDOFF-SENIOR-REPORT-DOC.md](senior-report-doc/HANDOFF-SENIOR-REPORT-DOC.md) |
| `senior-report-doc/STATUS.md` | [senior-report-doc/STATUS.md](senior-report-doc/STATUS.md) |

## Not archived

- `plans-1112/owner-answers-1112b.md`: the owner's raw answers file. The decisions themselves are recorded in
  `docs/capstone-report/owner-decisions-2026-09-27.md`.
- `senior-report-doc/part-1-draft-map.md`, `part-2-landed.md`, `part-3-metrics.md`: large working drafts feeding the
  senior report; not cited by path in the repo docs.
- Everything else under `~/hc-quiet-logs/`: raw probe logs, run data, `.json`/`.jsonl`/`.diff` files, scripts under
  `tools/`, trace and dump directories, and the other batch plan directories, none of which a doc cites as a `.md` file.

## Volatile scratch paths

`/tmp/claude-1000/...` paths cited in `queue.md` (about 671 references) were scratch files. They no longer exist and are
not archived. Paths under `/dev/shm` were likewise temporary.
