# Build-program Codex adversarial review (2026-10-15)

Reviewer: Codex CLI (`codex exec -s read-only`), driven by an Opus 5.5 L1, 2026-10-15. Targets: [contracts.md](../../plans/2026-10-15-build-program/contracts.md), [queue.md](../../plans/2026-10-15-build-program/queue.md), [RUNBOOK.md](../../plans/2026-10-15-build-program/RUNBOOK.md), `.claude/workflows/build-item.js`. Base `origin/main` @ `3b2236c`. Each finding was verified against the repo before any edit (receiving-code-review). No owner approval is recorded here.

**Result:** Codex `VERDICT: REVISE`, 7 findings. The Opus driver found 13 more. 20 found, 20 verified (1 downgraded, 2 partly accepted), 20 applied in part or in full, 0 rejected outright.

**Run notes.**
1. The first `codex exec` run hung: with a non-TTY stdin it printed `Reading additional input from stdin...` and waited about 4 minutes at 0.1 % CPU. It was killed and re-run with `</dev/null`, then exited 0. The same hang applies to RUNBOOK §10.2 (finding O-1).
2. The Opus driver edited the target files while the second Codex run was reading them, so some Codex line numbers point at the edited text. Each finding below is mapped to the current text.

## Prompt

```text
You are an adversarial reviewer. Repo: Asclexis (local-first health app), worktree at the current directory (branch docs/wave6-design = origin/main 3b2236c). Read-only.

Review these four files against the actual repository contents:
1. docs/plans/2026-10-15-build-program/contracts.md
2. docs/plans/2026-10-15-build-program/queue.md
3. docs/plans/2026-10-15-build-program/RUNBOOK.md
4. .claude/workflows/build-item.js
(The lane files docs/plans/2026-10-15-build-program/lane-*.md are context; cite them only if the four files contradict them.)

Authorities to check against: CLAUDE.md (esp. "Hard invariants", ask-first files: modules/interpret_safety.py, modules/redaction.py, modules/faithfulness.py, modules/verifier_agent.py, auth/encryption incl. core/auth.py; collected-count slot = 1574), AGENT.md, docs/capstone-report/owner-decisions-2026-09-27.md, docs/capstone-report/architecture-engineering-contract.md, docs/agentic/orchestration.md, docs/agentic/recurring-failures.md, docs/features/TASK_LIST.md, docs/capstone-report/implementation-program.md, migrations/master and migrations/profile chains.
Open PRs not on main (assumed to merge as-is): #95 ASSIST-UTC, #97 ADHERE-TZ, #99 SCHED-OWNER, #82 rl-export-prompt-snapshot, #84 gamification v2 tasks 2,4, #94 wearables plans, #74 tailwind4 (draft, owner screenshot gate), #72 W-4 legacy abstain (needs MM-1 run), #68 rsi-loop-research, #61 (close after #72).

Hunt for, specifically:
- Wrong file paths: any path, module, function, test helper, script, or migration that the plan names but that does not exist in the repo (verify with ls/grep). Wrong line references.
- Dependency/order errors in queue.md: items scheduled before their prerequisites, items depending on unmerged PRs without saying so, cycles, Alembic down_revision collisions when two items add migrations to the same chain in parallel.
- Contract gaps in contracts.md: interfaces underspecified so two lanes could implement incompatibly; missing error/edge cases; contracts that contradict existing code signatures.
- Safety/privacy invariant violations (CLAUDE.md Hard invariants): per-profile isolation (ProfileDbSession vs master get_db), local-first (no network), redaction before export/external runner (D3/D12), audit logging on routes, no medical advice / citation markers (D11), dual migrations, Python 3.11 target, core.time.utcnow. Any item touching an ask-first file that is not flagged as an owner gate. Any recorded owner approval that the owner-decisions doc does not actually contain.
- Claim-protocol races in RUNBOOK.md and build-item.js: two workers able to claim the same item, non-atomic claim (check-then-write), stale claims never released, crash mid-item leaving inconsistent state, git push races, worktree collisions, shell injection via item ids/titles, unchecked command exit codes, verification asserted rather than run, any path where the workflow would commit/merge without owner gates.

Output contract (strict, nothing else):
First line: VERDICT: PASS | REVISE
Then one line per finding:
[BLOCKER|MAJOR|MINOR] file:line — finding (include the evidence: the real path/signature/line you checked)
```

Command: `codex exec -s read-only -C /mnt/c/Users/DangT/Documents/GitHub/hc-wave6-design -o /tmp/claude-1000/codex-build-program.txt "$(cat <prompt>)" </dev/null` (exit 0).

## Codex output (verbatim)

```text
VERDICT: REVISE
[BLOCKER] docs/plans/2026-10-15-build-program/contracts.md:35 — I-15 lists `ALLOW`, `BLOCK`, and `UNAVAILABLE` but does not require `BLOCK` and `UNAVAILABLE` to suppress the answer; consumers could fail open on the medical-advice judge, contrary to `CLAUDE.md:61` (D11).
[MAJOR] docs/plans/2026-10-15-build-program/queue.md:68 — `head literal` is not a concrete file path, so the shared-file check cannot detect overlap between C-GAM2B’s profile-head edit and C-P6’s listed `test_care_tasks.py`, `test_profile_migrations_sqlcipher_fallback.py`, and `test_source_spans.py` edits (`queue.md:84`; `RUNBOOK.md:104`).
[MAJOR] .claude/workflows/build-item.js:60 — `PLANCHECK_SCHEMA` permits `go: true` without `gates_quoted`; the final PR body then substitutes `none` (`build-item.js:232`) and may proceed to `gh pr ready` (`:233`) despite RUNBOOK §4 requiring gate verification.
[MAJOR] .claude/workflows/build-item.js:73 — `red_green_output` is optional and the workflow advances on `status === "done"` (`:174`); final verification also returns unstructured agent text (`:227-237`). The workflow can present RED/GREEN or acceptance as complete without requiring that evidence, though RUNBOOK §6 requires command output (`RUNBOOK.md:123-135`).
[MAJOR] docs/plans/2026-10-15-build-program/RUNBOOK.md:87 — The post-claim step requires only a lock recheck; it does not require recalculating `SLOTS`, despite the rule at `:56` to release the highest-numbered claim when concurrent claims exceed two. Concurrent claims for different items can exceed the queue’s two-code-item cap (`queue.md:13`).
[MAJOR] docs/plans/2026-10-15-build-program/RUNBOOK.md:80 — If worktree creation succeeds but commit, push, or PR creation fails, `set -e` exits without removing the worktree or local branch. No claim PR exists for the stale-claim recovery rule to release, and a retry at the same `WT` path will fail.
[MINOR] docs/plans/2026-10-15-build-program/contracts.md:24 — I-4 names `api.medications._schedule_for_medication` but gives no callable signature or return contract, unlike I-1 and I-3; D-1 and D-2 therefore lack the interface they are told to implement against.```

## Responses to Codex findings

| # | Codex finding | Verified against | Verdict | Change |
|---|---|---|---|---|
| C-1 | BLOCKER, contracts I-15: no rule that `BLOCK`/`UNAVAILABLE` withhold the answer | The PARA-1-R3 plan §5 (`audit/2026-09-25/waves/scaffold/PARA-1-R3.md:98-108`) and owner PARA-R3-Q2Q3 "Fail closed" (`owner-decisions:117`) already bind fail-closed, so nothing fails open today. The cross-lane contract did not restate it, though | **Accept, downgraded to MINOR** (the gap is in the contract text, not the design) | I-15 now says that any result other than `ALLOW` withholds the answer, citing `:117` |
| C-2 | MAJOR, queue C-GAM2B: "head literal" is not a path, so Task 0's shared-file check cannot see a clash with C-P6 | C-GAM2B has no `depends_on` on C-P6, and waves are dependency layers (queue rule 3), so the two can run together. C-P6 lists the 3 literal files by name | **Accept** | The C-GAM2B row names the files, as the D-2 row does |
| C-3 | MAJOR, build-item.js: `go: true` without `gates_quoted` lets the PR body say "none" | `PLANCHECK_SCHEMA.required` was `['go','stop_reasons']`, and the Verify prompt substitutes `none` | **Accept** | `gates_quoted` and `skipped_tasks` are now required. Verify re-reads the row's gates against owner-decisions before `gh pr ready` |
| C-4 | MAJOR, build-item.js: `red_green_output` is optional, and Verify returns free text | `IMPL_SCHEMA.required` lacked it | **Partly accept** | `commits` and `red_green_output` are now required. The free-text Verify return stays: RUNBOOK §10.1 has L0 re-run one acceptance command itself (orchestration §2 step 5), and that re-run is the check |
| C-5 | MAJOR, RUNBOOK §3: the post-claim re-check skips the slot count | The Race row requires it, but snippet step 4 named only the lock | **Accept** | Step 4 now re-runs the slot count too |
| C-6 | MAJOR, RUNBOOK §3: a failed commit, push or PR create leaves an orphan worktree, branch or remote branch | True once `set -e` (O-5) aborts the snippet midway, and a retry at the same `WT` path fails | **Accept** | An `ERR` trap removes only what this claim created: the remote branch if it was pushed, the worktree and the local branch. `bash -n` passes |
| C-7 | MINOR, contracts I-4: no signature | `gh pr diff 99` gives `async _schedule_for_medication(profile_db: AsyncSession, schedule_id: str, medication_id: str) -> Optional[MedicationSchedule]`, `None` for an unknown id and 422 for another medication's schedule | **Accept** | I-4 carries that signature |

## Opus driver findings (same review pass, verified first)

| # | Sev | Location | Finding and evidence | Change |
|---|---|---|---|---|
| O-1 | MAJOR | RUNBOOK §10.2 | `codex exec` without `</dev/null` hangs on a non-TTY stdin. Seen live in this run | Added `</dev/null` to both `codex exec` lines, with a one-line reason |
| O-2 | MAJOR | contracts I-2 | `be/scripts/legacy_eval_gate.py` is wrong. `gh pr diff 72 --name-only` gives `scripts/legacy_eval_gate.py` (repo root) | Path fixed |
| O-3 | MAJOR | RUNBOOK §4 step 5 | The check reads only **non-draft** PR diffs. A just-claimed item is a draft with an empty diff, so two running items that share a file both pass (queue rule 2) | The check now also intersects the queue-row file lists of the other open `[claim:` PRs. Parked drafts that have released their slot stay exempt |
| O-4 | MAJOR | RUNBOOK §3, §4, §8; build-item.js | A stopped item kept its `[claim:` title, so it held a code slot until it went stale (24 h, and every comment resets that clock). Two stops would halt the whole 2-slot box, against queue rule 1 ("a PR that waits holds no slot") | New `[blocked:<runtime>]` title frees the slot, and L0 retitles to resume. The workflow's `block()` helper runs on every stop after the claim: Task 0, implement, review, fix round. Verify FAILED/BLOCKED also retitles |
| O-5 | MAJOR | RUNBOOK §3 snippet | The checks were comments ("must print nothing") with no `set -e`. A scripted launcher went on after a failed check or a failed push, and `gh pr create --head` could then open a PR on another claimer's branch of the same name | `set -euo pipefail`; the lock and slot results are tested; the claim aborts if the branch already exists on origin |
| O-6 | MAJOR | queue B-3 | B-3 is "ready", but its gates PR3-TIER and PR3-S5N are unanswered and not marked merge-only, so RUNBOOK §4 step 3 would stop it at Task 0 | The row says that the tasks these gates govern are skipped until answered (§4 step 3). No gate state changed |
| O-7 | MINOR | contracts §b, §c; queue | "Rebases" contradicts RUNBOOK §9 rule 6 (no force-push), and owner PR68-SYNC (`owner-decisions:158`) chose a merge over a force-push rebase | Glossary line: "rebase" here means `git merge origin/main` |
| O-8 | MINOR | contracts §b | No order row for `.gitignore`, which W-8 and F-10 both edit (`git show origin/docs/rsi-loop-research:.gitignore` adds `!.claude/settings.json`, `!.claude/hooks/`). The program orders it at `implementation-program.md:155` | Row added: F-10 → W-8, own lines |
| O-9 | MINOR | contracts §b | `be/tests/test_safe_chat_prohibited.py` is in both #72's diff and B-3's file list, with no order row | Added it to the #72 → B-3 row |
| O-10 | MINOR | queue C-P6 | C-P6 edits `be/core/database.py`, which holds the SQLCipher checks (`core/database.py:28`, `:71-76`), but its ask-first column omitted that file | Added to ask-first, marked as the FK pragma edit named by D5 (`owner-decisions:14`, "pragma ON for master + profile engines") |
| O-11 | MINOR | queue, owner prompt 2 | TW4-SHOTS is listed as a question, but it was answered at `owner-decisions:140` ("I compare them myself") | Removed from the prompt, with a note that E-4 waits on the owner doing that comparison |
| O-12 | MINOR | RUNBOOK §4 step 2 | No command checks a `depends_on` that is a queue ID (such as "E-3 merged") | Added a `gh pr list --state merged` title-suffix check. PRs merged before this program are checked by number |
| O-13 | MINOR | RUNBOOK §3 Lock | The lock regex `^[a-z]+/g-c5-` also matches a `g-c5-plan-…` branch (G-C5 vs G-C5-PLAN, the only such pair among the 51 IDs) | G-C5 slugs never start with `plan`, and a G-C5 lock check ignores a `g-c5-plan-` branch |

**Checked and found correct:** the slot lines `CLAUDE.md:30`, `:34` and `AGENT.md:76` (1574); profile head `012_pinboards` and its 4 literals; master head `002_backup_schedules`; `_get_alembic_config(section)`; the current `route_client` signature (I-9 appends to it); `core.database.async_session_maker` and `core.denial_audit._state` (I-12); `ValidatedResponse` in `modules/rag.py:103`; `get_model_runner`; the `core/time.py` anchors `:12`, `:17`, `:27`; `scripts/generate_docs_index.py`; `.gitignore:45`; the `codex exec` flags `--add-dir` and `-o`; `codex-companion.mjs` 1.0.4 `adversarial-review --wait --base`; the 51 queue rows; the existence of every `be/` and `fe/` path (each missing path is a planned new file or comes from an open PR); the gates marked "signed" in the queue (D5, P7-ROUTE, RESET-AUDIT-OWNER, GAM2-PLAN-APPROVAL, O-2 answered). No queue row records an owner approval that owner-decisions lacks.

**Verification run:** `bash -n` passes on the extracted claim snippet. The workflow passes `node --check` when wrapped in an async function, since a workflow script may use a top-level `return`. The lock, slot and dependency `gh` queries ran read-only against the live repo and returned 0 errors. pytest was not run.
