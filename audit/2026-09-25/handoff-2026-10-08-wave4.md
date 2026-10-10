# Handoff — Wave 4 mid-merge (2026-10-08)

**Last Updated:** 2026-10-08
**For:** the next L0 Program Orchestrator session (Asclexis, HealthCentral repo). The previous session's context is gone; everything needed is in this file and the files it names.
**Rule:** the owner merges; L0 never merges, never edits product code, never signs a gate. Stop at every owner gate and every PR merge.

## 1. Read first

1. `CLAUDE.md`, `AGENT.md`, `docs/agentic/orchestration.md`, `docs/agentic/recurring-failures.md`.
2. On branch `docs/wave4-close` (worktree `../hc-l0-docs`, pushed, no PR yet): [`waves/wave-4-L0-notes.md`](waves/wave-4-L0-notes.md) — every L0 verification this wave; this file.
3. On `origin/main`: [`waves/scaffold/README.md`](waves/scaffold/README.md) (readiness of every remaining phase, wave packing, owner questions 5-8), [`waves/scaffold/REVIEWS-2026-10-07.md`](waves/scaffold/REVIEWS-2026-10-07.md) (Fable and Codex findings), `docs/capstone-report/owner-decisions-2026-09-27.md` (rows dated 2026-10-07; the PARA-1-R2 row is on `docs/wave4-close` only).
4. L1 reports, each on its PR branch: `audit/2026-09-25/waves/wave-4-L1-A.md` (take the copy on `fix/p5-utcnow-migration`: it has both phases), `wave-4-L1-B.md` (Phase 1 on `fix/npm-audit-2`, Phase 2 on `fix/dev-ps1-install`), `wave-4-L1-C.md` (on `docs/w10-governance-amendments`).
5. `audit/2026-09-25/handoff-2026-09-28-execution-orchestrator.md` §4-§7 (L1 / L2 / reviewer / Codex brief templates).

## 2. State

`origin/main` = `777adf5`. Backend collected 1370 (`CLAUDE.md:30`, `:35`, `AGENT.md:76`). Vitest 195 in 34 files; Playwright chromium 31 listed. Waves 0-3 merged and closed (PRs #49, #50).

Open PRs, all L0-verified at the head shown, CI 6/6, MERGEABLE CLEAN on 2026-10-08. No L1 agent is running.

| Order | PR | Phase | Head | Worktree | Notes for the refresh |
|---|---|---|---|---|---|
| 1 | #51 | PROHIBITED-PARAPHRASE measure-only | `3d0d663` | `../hc-para-measure` | slots → 1374 (+4, HC-PARA-001…004). `interpret_safety.py` NOT edited |
| 2 | #53 | W-10 governance + 3 fold-ins | `86de589` | `../hc-w10` | docs-only; touches `CLAUDE.md:25,:50,:60,:62`, `data-privacy.md`, `hipaa-controls.md:49,:52`, `docs/INDEX.md` |
| 3 | #54 | P5 utcnow migration (+ TIME-03) | `9b80860` | `../hc-p5` | slots 1377 alone; after #51 re-measure (expect 1381). Add/add conflict on `wave-4-L1-A.md`: take the P5 copy. Adds a `TASK_LIST.md` session note |
| 4 | #52 | NPM-AUDIT-2 (lockfile: `source-map-js` 1.2.2 only) | `7281faa` | `../hc-npm-audit-2` | frontend PR: Windows `npm ci` + vitest on refresh |
| 5 | #55 | DEV-PS1-INSTALL | `52b2c39` | `../hc-devps1` | add/add conflict on `wave-4-L1-B.md` with #52: keep both sections. Regenerates `docs/INDEX.md` |

Refresh procedure for every PR after the first (unchanged from Wave 3): `git merge origin/main` (never rebase) → regenerate `docs/INDEX.md` + `docs/_link_graph.json` by script (`python3 scripts/generate_docs_index.py && python3 scripts/docs_lint.py --link-graph`), never by hand → `--collect-only` and rewrite the three count slots to the MEASURED number only if it changed → full suite under `flock /tmp/claude-1000/hc-pytest.lock` (backend PRs) or Windows `npm ci` + full vitest (frontend PRs) → push → `gh pr checks <n>` 6/6. Then L0 verifies in `../hc-l0-verify` (detached at the PR head): mergeable CLEAN, file list = plan, source diff versus the last L0-verified head (expect 0 lines outside the merge), index `--check` fresh, one acceptance test, count = slots, one break-it for code PRs (delete by line number after `grep -n`, restore with `git checkout`). Log it in `wave-4-L0-notes.md`, commit, push, hand the PR to the owner, wait for "merged".

Break-its that worked at the heads above: #51 delete `interpret_safety.py:57` → 2 of 4 HC-PARA tests fail; #54 `models/audit.py:63` back to `datetime.utcnow` → `scripts/time_source_lint.py` reports it; #55 `dev.ps1:642` `-ne` → `-eq` → `scripts/check_dev_ps1_install.ps1` 14/22 (run on Windows: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File 'C:\Users\DangT\Documents\GitHub\hc-l0-verify\scripts\check_dev_ps1_install.ps1'`).

## 3. Owner decisions in force for Wave 4 (verbatim rows in owner-decisions)

PARA-1-REDO and PARA-1-R2 (measure first; **one more round**: keep the live patterns, derive a list that loses 0 of the 215 pinned sentences, add a fourth independent held-out set with app-instruction text, measure before any edit; L1 also proposes a run-time bound under 0.1 s per check — ask the owner to confirm that bound, and whether to consider "stop doing this with patterns" instead) · P5-SCOPE (TIME-03 in) and P5-IMPORT · GOV-BG, GOV-D11, W-10-REST, W10-Q4 / W10-Q5, W10-HIPAA · NPM-MAJORS-RUN, FE-SEQ, MAJORS-TIED, DEV-PS1-FIRST, TW4-BROWSERS, TW4-VISUAL · AUDIT-ORDER (plan only, with AUDIT-DENIALS) · G-C2-DEFER.

Owner directions on reviews (ledger 2026-10-07; also in the L0's memory): run a Codex review on every large plan (Codex's configured default is `gpt-6-luna` at xhigh; "6.1 sol" was never confirmed as a model ID — ask); for large stages such as the frontend sequence, have Fable 5.1 (`Agent` with `model: "fable"`) adversarially review the planning briefs before dispatch.

## 4. Next steps, in order

1. **Merge queue**, strictly serial: #51 → #53 → #54 → #52 → #55, with the refresh and L0 verification above before each hand-over.
2. **Dispatch the rest of Wave 4** as dependencies land (at most 2 code L1s at once, one L2 per L1, every full backend suite under flock):
   - PARA round 2 (after #51): measure-only again; no `interpret_safety.py` edit until the owner signs a list.
   - React Router 7 (after #52): brief in `waves/scaffold/REACT-ROUTER-7.md` + required amendments in REVIEWS §1 (`\$LASTEXITCODE`, nested lockfile diff — reuse the script in Amendment 2 of `docs/plans/2026-10-04-NPM-audit-fix.md`, a lazy-route check that can fail).
   - Tailwind 4 (after #52, #55 and React Router 7): `waves/scaffold/TAILWIND-4.md` + REVIEWS §1 (Task 0 stops unless #55 is merged; computed-style Playwright checks on seeded data; CI screenshots of 10 routes for the owner; browser floor in README and user docs; `tailwind-merge` 3 approved; MAJORS-TIED rule for `jiti` 2 and new packages).
   - AUDIT-ORDER + AUDIT-DENIALS plan (plan-only, architectural: Codex review; touches ask-first `core/audit.py`, so nothing is edited before the owner approves the plan).
   - P4-deferred N8 and N10 (after #53; docs).
   - After #54 merges, P5 unblocks W-4, W-2 (also needs #53) and P6: re-read their scaffold packs; W-4 needs its plan amended first (the SAFE-CHAT branch at `api/assistant.py:879-892` overwrites W-4's abstention; owner question OQ-1 / W4-EXPEDITE is unasked).
3. **Owner questions still open** (ask at most 4 per prompt): scaffold README §3 items 5-8 (W-4 OQ-1 + W4-EXPEDITE; W-8 EMB-REV + Q-OFFLINE; W-2 O-2 date format; P7 vs W-11a PR-1 reset-route audit row); from W-10: the `CLAUDE.md:60` closure clause naming the two export routes, BG-WARN-INTERP, and the L1's reword of `hipaa-controls.md:52`; PARA round-2 run-time bound.
4. **Close Wave 4** on `docs/wave4-close` when its PRs are merged: `audit/2026-09-25/waves/wave-4.md` (merged table like `wave-3.md`); register the new owner items in `docs/capstone-report/implementation-program.md` (lists in `wave-4-L0-notes.md` and the three L1 reports, including BG-WARN-INTERP, the remaining compliance-doc overclaims, the `dev.ps1` items, `AchievementsWidget.tsx:45` local-time parse, the lint's aliased-import gap); update the stale program rows the scaffold found (`:425/:490`, `:426/:491`, `:461`); add the recurring-failures §1 instance from #55 (stubbed checks green over a broken real `npm` call); update the specs-compliance matrix rows these PRs change and recount BY SCRIPT (`audit/2026-09-25/swarm-2026-09-27/wave3/scorecard_count.py`); run `docs_lint`, `generate_docs_index --check`, `feature_list_lint`, `repo_hygiene_check`, `harness_drift_check`; append a dated ledger section with a RESUME POINT; open the PR.
5. **Delivery Map**: https://claude.ai/artifact/JBYpfBuCegbdCfbTJzYtxi (v5, 7 Oct; private). Republish after the wave closes (`Artifact` read the URL, edit, publish with the same `url`). The older URL `DzJ89t8zJo4tPf7NjzctxV` is read-only.

## 5. Environment and lessons

- Venv: `~/venvs/asclexis-311/bin/python` (3.11.16, no pip → `uv pip install -p ...`). Always `HF_HUB_OFFLINE=1`. 12 GB RAM.
- Frontend runs on Windows only: `powershell.exe -NoProfile -Command "cd C:\Users\DangT\Documents\GitHub\<wt>\src\frontend; npm ci; npx vitest run"`. In a bash double-quoted string write `\$LASTEXITCODE`.
- `gh pr edit` fails (use `gh api -X PATCH`); `gh pr checks` has no `--json`. The route to GitHub drops now and then ("no route to host"): retry.
- The repo is public; Actions minutes are no longer a constraint. GitHub CI stays the merge gate (local cannot run E2E; the eval gate does not exit locally).
- Every Agent prompt includes: `Output style: follow ~/.claude/rules/common/subagent-output.md (i-have-adhd)`. Roles: L1 = `general-purpose` opus; L2 = `general-purpose` sonnet; reviewers = `code-reviewer` + `security-reviewer` (opus).
- A PR head can move after L0 verifies it (it happened to #51): re-read the head SHA before handing a PR over, and re-verify if it changed.
- L1s cannot tick owner boxes; L0 records sign-offs from the owner's own chat answers, verbatim, in owner-decisions.
- When L0 asks the owner to sign something, state the downside it measured as well as the gain: PARA-1 was first signed on in-sample figures and had to be re-opened.
- Agent reports are leads. Verify each claim that matters; say what was not verified.
