# Handoff — Wave 4 merged, close-out pending (2026-10-09)

**Last Updated:** 2026-10-09
**For:** the next L0 Program Orchestrator session (Asclexis, HealthCentral repo). Supersedes [handoff-2026-10-08-wave4.md](handoff-2026-10-08-wave4.md) for state; that file's §5 environment notes still apply.
**Rule:** the owner merges; L0 never merges, never edits product code, never signs a gate. Stop at every owner gate and every PR merge. Verify every agent claim that matters; say what you did not verify.

## 1. Read first

1. `CLAUDE.md`, `AGENT.md`, `docs/agentic/orchestration.md`, `docs/agentic/recurring-failures.md`.
2. On branch `docs/wave4-close` (worktree `../hc-l0-docs`, pushed, no PR yet): [`waves/wave-4-L0-notes.md`](waves/wave-4-L0-notes.md) (every L0 verification this wave, with what was not re-run) and `docs/capstone-report/owner-decisions-2026-09-27.md` (all 2026-10-08 / 2026-10-09 rows are on this branch only, not on main).
3. L1 reports on main: `audit/2026-09-25/waves/wave-4-L1-A.md` (PARA measure + P5), `wave-4-L1-B.md` (NPM-AUDIT-2 + DEV-PS1; has two intro paragraphs and two "Merge order" headings from the add/add merge: tidy at close), `wave-4-L1-C.md` (W-10), `wave-4-L1-D.md` (React Router 7).
4. `audit/2026-09-25/handoff-2026-09-28-execution-orchestrator.md` §4-§7 (L1 / L2 / reviewer / Codex brief templates).

## 2. State

`origin/main` = `eb7de28`. Backend collected 1381 (`CLAUDE.md:30`, `:35`, `AGENT.md:76`). Vitest 197 in 35 files; Playwright chromium 33 listed (all projects 38). `npm audit` 7 (2 moderate, 5 high).

Wave 4 merges, all at the L0-verified head:

| PR | Phase | Merged head | main after |
|---|---|---|---|
| #51 | PROHIBITED-PARAPHRASE measure-only | `3d0d663` | `6e73fea` |
| #53 | W-10 governance + 3 fold-ins | `cf05786` | `6c13045` |
| #54 | P5 utcnow migration + TIME-03 | `b2743ac` | `98bd3c7` |
| #52 | NPM-AUDIT-2 | `4c82d6b` | `f428a99` |
| #55 | DEV-PS1-INSTALL | `e980e4a` | `87accae` |
| #57 | React Router 7 (merged without a refresh after #55; CI was green at its head) | `af14128` | `eb7de28` |

Open PR: **#56** AUDIT-ORDER + AUDIT-DENIALS plan (plan only, not approved for execution), head `f141edd`, branch `docs/audit-order-plan`, worktree `../hc-audit-order`. **Merge conflict on `docs/INDEX.md` and `docs/_link_graph.json` only** (L0 dry run: `git merge-tree` lists no other file). Refresh: `git merge origin/main`, resolve both by `python3 scripts/generate_docs_index.py && python3 scripts/docs_lint.py --link-graph`, never by hand; then L0 verifies (file list = plan + 7 review files + index; 0 under `src/ scripts/ config/ .github/`; `--check` fresh; CI 6/6) and hands to the owner.

Not merged, kept as evidence: branch `test/para-round2-measure` @`7991d96` (union_r2 list; owner chose "Stop using patterns"). The blind fourth held-out set lives only in the old session scratchpad (sha256 `7e0830c0…`) and is gone; the measured numbers are in the L0 notes.

No agent is running.

## 3. Owner decisions recorded this session (verbatim rows on `docs/wave4-close`)

PARA-R2-BOUND, AO-BRIEF4, W10-HIPAA-52, C2-CLOSURE, OQ-1 (ABSTAIN_TEMPLATE), O-2 (ISO-8601), EMB-REV (pin approved), Q-OFFLINE (per call), PARA-1-R3 (**Stop using patterns**), BG-WARN-INTERP (fix in a small PR), RESET-AUDIT-OWNER (W-11a PR-1), RR7-Q1 (keep -dom), RR7-Q2 (Playwright spec, done in #57), RR7-Q4 (separate owner item), AO-DESIGN (D), AO-FAIL (fail closed), AO-SCOPE (irreversible set), AD-DENIALS (cross-profile 403s only).

Still unasked: **AO-ASKFIRST** (per-file approval: `core/audit.py` helper for option D, `core/auth.py:278-286` for D-B) and **approval of the AUDIT-ORDER plan for execution**; `engines.node` `>=22` vs vite `>=22.12.0` (RR7 pack Q3); W-4 OQ-2 / OQ-5 / CI-SEED; W-2 S-3/O-3, P0-D-MOOT, EXPORT-QUESTIONS; AGENT-PASS-LINE (`CLAUDE.md:31` "1288 pass", `AGENT.md:76` "1269 / 1268" are stale).

## 4. Next steps, in order

1. **#56 refresh** (above), hand to owner. Then ask AO-ASKFIRST and plan approval (state the downsides; §12 of the plan lists 8 residual risks, none re-reviewed after the security pass).
2. **Close Wave 4** on `docs/wave4-close`: `audit/2026-09-25/waves/wave-4.md` (merged table above, like `wave-3.md`); tidy `wave-4-L1-B.md`; register new owner items in `docs/capstone-report/implementation-program.md` (list in §5); update stale program rows (`:425/:490`, `:426/:491`, `:461`); recurring-failures §1 instance from #55 (stubbed checks green over a broken real `npm` call) and the RR7 empty-`<main>` check that could not fail until rewritten; specs-compliance matrix rows these PRs change, recount BY SCRIPT (`audit/2026-09-25/swarm-2026-09-27/wave3/scorecard_count.py`); run `docs_lint`, `generate_docs_index --check`, `feature_list_lint`, `repo_hygiene_check`, `harness_drift_check`; dated ledger section with a RESUME POINT; open the PR (it carries every owner row of this session onto main).
3. **Delivery Map**: https://claude.ai/artifact/JBYpfBuCegbdCfbTJzYtxi (v5, private). `Artifact` read, edit, publish with the same `url` after the close PR.
4. **Dispatch** (at most 2 code L1s; every full backend suite under `flock /tmp/claude-1000/hc-pytest.lock`; Windows for npm):
   - **Tailwind 4** — unblocked (#52, #55, #57 merged). `waves/scaffold/TAILWIND-4.md` + REVIEWS-2026-10-07 §1 amendments; signed TW4-BROWSERS, TW4-VISUAL, MAJORS-TIED, `tailwind-merge` 3. Large stage: Codex plan review + Fable 5.1 (`Agent` `model: "fable"`) adversarial brief review before dispatch (owner direction).
   - **BG-WARN-INTERP** small frontend PR: render the existing break-glass warning on the Lab Interpreter page + one test (`api/interpretations.py:476-492` reaches the external provider; L1-reported, not re-read by L0).
   - **C2-CLOSURE** docs PR: add to `CLAUDE.md:60` "only `GET /export/csv` and `GET /export/json`; no other export is exempt".
   - **PARA-1-R3 plan**: architectural plan for recall in another layer (agent draft path / PARA-2 / classifier); Codex review; `interpret_safety.py` stays unedited.
   - **W-4** (P5 merged): amend its plan first (SAFE-CHAT branch at `api/assistant.py:879-892` overwrites W-4's abstention; OQ-1 answered ABSTAIN). **W-2** (P5 + W-10 merged; O-2 answered). **P6** (P5 merged; Codex). Re-read their scaffold packs; line numbers moved after P5 (+1 in many `api/*.py`).
   - AUDIT-ORDER execution only after AO-ASKFIRST and plan approval.

## 5. New owner items to register at close (evidence in the L0 notes)

1. **Unaudited patient-data writes** (~22 routes: medication update / schedules / dose logs, assistant sessions and memory settings, 8 model-settings routes, 2 notifications routes) — breaks the CLAUDE.md audit invariant. Source: AUDIT-ORDER plan §3.1 (agent-measured).
2. **`log_auth_event` (`core/audit.py:490`) has no non-test caller** (L0 grep on main): login/logout likely unaudited.
3. `security/audit_middleware.py:5` docstring claims DB persistence; `log_to_db` (`:33`) is never read.
4. `scripts/check_sqlcipher.py` (encryption check) is not run in CI.
5. **FE-BKUP-001 flaky** under load (3 failures this wave, passes alone).
6. RR7-Q4 `SettingsPage.tsx:952-954` `startsWith('/')` admits `//x`; check `cookie` / `set-cookie-parser` stay out of the client bundle.
7. From the earlier lists: BG-WARN-INTERP (being fixed), remaining compliance-doc overclaims (`data-privacy.md:33,:47,:61`, `hipaa-controls.md:50-51,:83-88`, `docs/compliance/README.md:14-18`, `models/audit.py:4,:25`), `dev.ps1` items, `AchievementsWidget.tsx:45` local-time parse, the time lint's aliased-import gap, feedback `_emit_audit` fail-open (`feedback.py:40-57`).

**Ponytail over-engineering audit** (owner-requested 2026-10-09; report was in the old scratchpad, now gone). Verified highlights, offered to the owner as one cleanup PR, not yet answered: 8 unused dependencies (backend `pypdf`, `numpy`, `python-dateutil`, `aiofiles`; frontend `@radix-ui/react-dialog`, `react-tabs`, `react-tooltip`, `date-fns`: 0 imports, L0 re-grepped); dead files `src/backend/scripts/model_manager.py`, `scripts/detect_hardware.py`, `useSpeechRecognition.ts`, `CategoryBadge.tsx`; committed junk `.vite/`, `.bg-shell/manifest.json`, empty root `package-lock.json`; 64 raw `audit/**/*-codex.txt` (20 inbound links); 26 merged local branches without a worktree. Re-run `/ponytail:ponytail-audit` if the owner wants the full table.

## 6. Environment changes this session

- **Devin MCP** worked (SWE-2 Max, `devin_session_create` with `devin_mode: "swe-2-max"`; it did the #53 refresh and PARA round-2 phase 1), then disconnected (connect timeout). `devin_session_gather` was blocked by the permission classifier; read sessions with `devin_session_interact` / `devin_session_events`. Devin works in a cloud clone: no local worktrees, venv or Windows. The owner's routing (`~/.claude/CLAUDE.md`, updated 2026-10-09): Opus orchestrates/reviews, Sonnet implements, Haiku explores, Devin takes about half of the Sonnet/Haiku work; fall back to Claude when Devin fails.
- `/doctor` cleanup applied 2026-10-09 (user scope only): `stitch`, `caveman` MCP disabled for this project; `megacave`, `ultracave` skills off; Go/Python/TypeScript rule files under `~/.claude/rules/` now load by `paths:`; broken symlink `~/.claude/skills/*` removed. Backups `~/.claude.json.bak-doctor-20261009`, `~/.claude/settings.json.bak-doctor-20261009`.
- The machine ran at load ~37 during Windows npm runs; docs scripts on `/mnt/c` can exceed 2 minutes: run them in the background.
- Codex review: `codex exec -s read-only -C <worktree> -o <out> "$(cat <prompt>)"`; model reported "GPT-6", effort not exposed. Prompts and outputs for #56 are committed under `audit/2026-09-25/swarm-2026-09-27/reviews/AUDIT-ORDER-*`.
