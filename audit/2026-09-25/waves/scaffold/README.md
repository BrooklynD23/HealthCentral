# Wave 4+ scaffolding packs (2026-10-07)

Readiness packs for every phase not marked done in the program's W-plans table. One file per phase; the first line of each is its verdict. Measured at worktree `hc-scaffold` (branch `docs/wave4plus-scaffold` = `origin/main` `6b4dd84` + the Wave 3 close docs, PR #49 open). Nothing under `src/`, `scripts/`, `docs/` or any plan file was edited; the packs list plan amendments, they do not apply them.

**Fact that gates every Task 0:** no owner-decisions row dated 2026-10-04 or 2026-10-07 (PARA-1, AUDIT-ORDER, NPM-MAJORS-RUN, GOV-BG / GOV-D11, S-C3-1, OG-4…) is on `origin/main` yet: `git show origin/main:docs/capstone-report/owner-decisions-2026-09-27.md | grep -c PARA-1` → 0 (L0 re-ran). The W11b plan's `[x]` ticks for S-C3-1 / S-C3-3 are likewise only on `docs/wave3-close`. Merge PR #49 before any Task 0 greps main for a gate.

## 1. Verdicts

Verdict key: READY = hard deps on `origin/main` and every needed gate signed; GATED = deps met, named gates unsigned; BLOCKED = a hard dependency is not merged (pack has sections 1-3 only). P5 marker used for every "P5 not merged" claim: `git grep -c time_source_lint origin/main -- .github/workflows/ci.yml` → 0 (L0 re-ran).

| Phase (pack) | Verdict | Blocking dependency / unsigned gates | Files-overlap group | Suggested wave |
|---|---|---|---|---|
| [PROHIBITED-PARAPHRASE](PROHIBITED-PARAPHRASE.md) | READY (2 conditions) | PARA-1 signed (`owner-decisions:62`, not on main until #49). Condition: the signed list regresses recall on plain diagnoses (agent probe, lead) → re-ask before editing `interpret_safety.py` | SAFETY (`modules/interpret_safety.py`, `tests/`) | 4 |
| [P5](P5.md) | GATED | deps P2 `cff3827`, P4 `6b4dd84`, W-6 `2f0cb6f` all rc 0; D13 signed (`:23`). Unsigned: TIME-03 scope, `api/profiles.py:13` import removal (7th auth line), CI-SEED (optional) | PROFILES-CI (`api/profiles.py`, `ci.yml`, 30 product files) | 4 |
| [W-10](W-10.md) | GATED | GOV-BG / GOV-D11 signed (`:65`); Q3, Q4, Q5 unsigned; Codex plan review owed | GOVERNANCE (`CLAUDE.md` invariant lines, `data-privacy.md`) | 4 |
| [NPM-AUDIT-2](NPM-AUDIT-2.md) | READY (no plan file) | NPM-MAJORS-RUN signed (`:64`); Q1 which plan document L1 executes | FRONTEND-DEPS (`package-lock.json`) | 4 |
| [REACT-ROUTER-7](REACT-ROUTER-7.md) | READY (serial after NPM-AUDIT-2) | NPM-MAJORS-RUN signed; plan Task 3 unsigned (excluded) | FRONTEND-DEPS (32 importer files, 15 test files) | 4-5 |
| [TAILWIND-4](TAILWIND-4.md) | GATED (serial after React Router 7) | `tailwind-merge` 2→3 not named in any signed row (`grep -c tailwind-merge owner-decisions` → 0); browser floor | FRONTEND-DEPS (up to 58 `.tsx`; overlaps W-3, W-2 frontend files) | 5 |
| [AUDIT-ORDER](AUDIT-ORDER.md) (+ AUDIT-DENIALS) | READY (plan-only) | AUDIT-ORDER row signed (`:63`); no plan file exists (this phase writes it); `core/audit.py` ask-first, untouched | AUDIT (new `docs/plans/` file only) | 4 |
| [P4-deferred](P4-deferred.md) | N8, N10 READY · N9 GATED · F1-F6 BLOCKED | N9: P8-B2-ORDER (packet `Owner decision:` lines unfilled). F1←W-3, F2←W-2+W-10, F3←W-7, F4←W-4, F5←W-8, F6←W-10 | DOCS (architecture docs; `pipelines.md:126-127` with DOC-PIPELINES-PROHIBITED) | 4 (N8, N10); 8 (F*) |
| [G-C2](G-C2.md) | GATED | S-C2-1/2/3 unsigned (W11b `:1946-1948`); owner generates locally | OPENWIKI (`openwiki/`, `CLAUDE.md:67` goes stale) | 4 (owner run) |
| [G-C5](G-C5.md) | GATED | P8 Brief 5 Q5a/Q5b unfilled; no plan yet | EVAL (`scripts/agent_eval_gate.py` neighbourhood) | 6+ |
| [RTN](RTN.md) | GATED | spec §9 unsigned, Q6 | none (cloud routine config) | owner |
| [SHOWCASE](SHOWCASE.md) | GATED | O-1…O-7 unsigned; plan unaudited; refresh triggers fired | DOCS/demo | owner |
| [W-4](W-4.md) | GATED (amended 2026-10-09, §4) | OQ-5 before dispatch; OQ-2 (pre-merge), CI-SEED (Task 5 Step 2) unsigned. P5 merged, OQ-1 signed | ASSISTANT (`api/assistant.py`, `ci.yml`, new `tests/legacy_eval/`) | 5 |
| [W-2](W-2.md) | BLOCKED | P5, W-10. After: S-2/O-2, S-3/O-3, P0-D-MOOT, EXPORT-QUESTIONS | EXPORT (`api/export.py`, `modules/export.py`, `ExportPage.tsx`) | 5 |
| [P6](P6.md) | BLOCKED | P5. D5 signed (`:14`); orphan-report review by design; `core/profile_database.py` listener (D5 names pragma, not file) | DB (`core/database.py`, `core/profile_database.py`, migration 013, `models/*`, `test_care_tasks.py`) | 5 |
| [P7](P7.md) | BLOCKED | P6. P7-ROUTE signed (`:32`); N-02 FTS decision; reset-route audit row owner (P7 vs W-11a PR-1) | PROFILES (`api/profiles.py` reset tuple, `tests/support/routes.py`) | 6 |
| [W-3](W-3.md) | BLOCKED | P5, W-10, W-4. After: O-5, O-1/VERIFIED-FALLBACK, O-2 veto | RAG (`modules/rag.py`, `api/observations.py`, `api/assistant.py`, trend `.tsx`) | 6 |
| [W-11a-PR-3](W-11a-PR-3.md) | BLOCKED | P5, W-4. Q-RUFF, Q-COV, CI-SEED unsigned | CI (`ci.yml`, `ci-and-quality-gates.md`) | 6 |
| [G-C3a](G-C3a.md) | BLOCKED | W-4. S-C3-1 signed (`:48`); S-C3-2 unsigned | EVAL (`docs/agentic/evals.md`) | 6 |
| [W-7](W-7.md) | BLOCKED | P5, P7 (behind P6). Plan's own Task 0 stop: expects 0 audit lines in `api/interpretations.py`, main has 15 (PR #48) | INTERP (`api/interpretations.py`, `modules/model_selector.py`, `modules/interpret.py`) | 7 |
| [W-11a-PR-1](W-11a-PR-1.md) | BLOCKED | P5, P7. OG-1, Q-AUD-LIST unsigned | PROFILES (`api/profiles.py`, `tests/support/routes.py`) | 7 |
| [W-8](W-8.md) | BLOCKED | P5, W-3, W-11a PR-3. Q-OFFLINE, Q-HASH, Q-FC, VERIFIED-FALLBACK, EMB-REV unsigned (EMB-REV and Q-OFFLINE can be asked now) | RAG/CI (`modules/rag.py`, `api/documents.py:867-871`, `ci.yml`, `.gitignore`, `core/config.py`) | 7 |
| [G-C1](G-C1.md) | BLOCKED | P5, W-2, P6, P7. S-C1-1, S-C1-2 unsigned | EXPORT/DB (`api/export.py`, migration 014, `test_care_tasks.py`) | 8 |
| [W-10b](W-10b.md) | BLOCKED | W-10, W-2, W-3 (W-6 merged). S6 | GOVERNANCE (`data-privacy.md` status lines) | 8 |

## 2. Proposed wave packing (Waves 4-9)

Rules: at most 2 code L1s at once (12 GB host); docs L1s are extra; merges serial on `CLAUDE.md`/`AGENT.md` slots, `api/profiles.py`, `ci.yml`, `modules/rag.py`, `api/export.py`. Everything below P5 is a chain: P5 → {P6 → P7 → W-7 / W-11a PR-1 / G-C1} and P5 → {W-4 → W-3 → W-8, W-11a PR-3 → W-8, G-C3a}. P5 is the single most unblocking phase.

| Wave | Code L1 A | Code L1 B | Docs / plan-only / owner | Needs before start |
|---|---|---|---|---|
| 4 | PROHIBITED-PARAPHRASE execution (measure-first; stop before `interpret_safety.py` edit if recall regresses), then P5 | NPM-AUDIT-2 → React Router 7 (serial) | W-10 (Codex plan review first), then P4-deferred N8 + N10; AUDIT-ORDER plan (architect + Codex); G-C2 owner run | PR #49 merged; PARA Q1; P5 Q1-Q3; W-10 Q3/Q4/Q5; NPM-AUDIT-2 Q1 |
| 5 | W-4 (Codex), then P6 (Codex; orphan report → owner → migration) | Tailwind 4 (Codex plan + Fable brief review; DEV-PS1-INSTALL fix first as its own PR) | W-2 after W-10 + P5 merge (Codex) | P5 merged; OQ-1/2/5; `tailwind-merge` 3; O-2 |
| 6 | P7, then W-11a PR-1 | W-3 (Codex; serial on `rag.py` after W-4) | W-11a PR-3; G-C3a | P6, W-4 merged; O-5, VERIFIED-FALLBACK; Q-RUFF/Q-COV; P7 N-02 |
| 7 | W-7 (Codex; amend Task 0 audit expectation; HC-INT-013 fixtures re-run after PARA) | W-8 (Codex; after W-3 + W-11a PR-3) | P4-deferred F1, F4 | P7, W-3, W-11a PR-3 merged; EMB-REV, Q-OFFLINE, Q-HASH, Q-FC; W-7 OG-1/2 |
| 8 | G-C1 (Codex) | — | W-10b; P4-deferred F2, F3, F5, F6; G-C5 plan (after Brief 5) | W-2, P6, P7 merged; S-C1-1/2; S6 |
| 9 | G-C5 execution (if Brief 5 signed) | — | P4-deferred N9 (after P8-B2-ORDER); RTN; SHOWCASE | owner sign-offs |

Program amendments the packing implies (not applied): `models/document_category.py` is a P5 → P6 shared file missing from the shared-file order list; `W-6 → P5` is satisfied (W-6 merged); `implementation-program.md:426,:491` and both NPM-MAJORS plan headers still say "not approved for execution" against `owner-decisions:64`; `:425,:490` still say PARA-1 unsigned; `:461` AUD-INTERP is stale after PR #48.

## 3. Owner questions, ordered by work unblocked (at most 4 per prompt)

1. **PARA-1 recall regression (PROHIBITED-PARAPHRASE Q1).** An agent probe (its own sentences; a lead, not a finding) found the signed candidate list misses plain diagnoses the current 11 patterns catch ("You have type 2 diabetes."). Options: (a) measure first in memory on a held-out + must-not-regress set and bring numbers back before any edit (recommended); (b) union old + new lists; (c) proceed as signed. Unblocks: Wave 4 L1 A.
2. **P5 scope (3 sub-questions, one prompt).** (i) TIME-03: leave `modules/badge_evaluator.py:84` out of P5 (recommended; a naive swap changes `api/medications.py:285` `earned_at.isoformat()` output, tripping P5's own no-serialization-change gate) or include it; (ii) confirm D13 covers exactly the 6 `api/profiles.py` swap lines; (iii) may P5 also delete the then-unused `from datetime import datetime` at `api/profiles.py:13` (7th auth-file line; recommended yes). Unblocks: P5 and the whole chain beneath it.
3. **W-10 Q3/Q4 + DP-4 wording.** Q3: name the external runner under "Local-first" (plan default: skip). Q4: slot handling. New: should `data-privacy.md` call W-6 "merged; conformance unverified" (plan rule, recommended) or amend the check? Also: fold LOCAL-07, DOC-OVERCLAIM (`:33`, `:35`), CLAUDE-FAILURE-COUNT into W-10 as separate commits (recommended) or leave as owner items. Unblocks: W-10, then W-2, W-3, W-10b.
4. **NPM-AUDIT-2 Q1 + Tailwind 4 Q1.** Which document does L1 execute for NPM-AUDIT-2 (recommended: reuse `2026-10-04-NPM-audit-fix.md` with an "Amendment 2" first commit)? Approve `tailwind-merge` 2 → 3 by name in the Tailwind 4 PR (recommended yes)? Does NPM-AMEND-1's transitive-major rule carry over (signed for 2 named packages only)? Unblocks: Wave 4 L1 B and Wave 5.
5. **W-4 OQ-1 / W4-EXPEDITE.** Which template on `is_valid=False` (T1 ABSTAIN recommended; note SAFE-CHAT already returns ESCALATE on the prohibited trigger, so the golden case `abstain-prohibited-advice` must expect escalation). Run W-4 before P5 (W4-EXPEDITE)? Recommended no. Unblocks: W-4 → W-3, W-11a PR-3, G-C3a.
6. **W-8 EMB-REV + Q-OFFLINE** (askable now): pin `all-MiniLM-L6-v2@1110a243fdf4706b3f48f1d95db1a4f5529b4d41`; per-call `local_files_only` vs process-wide `HF_HUB_OFFLINE`. Unblocks nothing until Wave 7 but removes two gates from the critical path.
7. **W-2 O-2** date format: ISO-8601 in the doctor summary (recommended) or accept `[DATE-REDACTED]`. Blocks W-2 Task 3.
8. **P7 / W-11a PR-1 overlap**: who writes the `/profiles/test/reset` audit row (plan 07 Task 2 Step 3 `synthetic_test_reset` vs W-11a `profile.test_reset`, HC-PAUD-003 asserts exactly one). Recommended: W-11a PR-1 owns it; P7 stays route-only as P7-ROUTE says.

Later: G-C2 S-C2-1…3; G-C5 Q5a/Q5b; P6 `core/profile_database.py` listener (D5 names the pragma, not the file); W-3 O-5; W-7 OG-1/OG-2 and prohibited-draft behaviour; W-11a Q-RUFF (a) / Q-COV; G-C1 S-C1-1/2; RTN §9; SHOWCASE O-1…O-7; N9 P8-B2-ORDER.

## 4. Verified by L0 (re-run, not taken from agents)

- Ancestry rc 0 on `origin/main` for all 14 Wave 0-3 merge SHAs (`6b4dd84 cff3827 d21c59d 2f0cb6f 040cf8c cbabed1 0bad019 ee5721d 930c678 22491e2 c4d407e 29c11e8 25c993e 242f7a0`).
- `datetime.utcnow` product hits 101 lines / 30 files; plan-05 lint pattern `datetime\.(utcnow|utcfromtimestamp)` (`:411`) matches `core/time.py:18`; plan `:455` YAML `- name: Lint: deprecated…` has the unquoted colon; `api/profiles.py:13` import + 6 uses; `api/medications.py:285` `earned_at.isoformat()`; `test_care_tasks.py:809,825` `"012_pinboards"`.
- `modules/rag.py:839-842` sets `prohibited_advice = True`; PARA-1 absent from `origin/main`.
- `api/interpretations.py` 15 audit lines, `_audit_interpretation` at `:38`; `api/documents.py:867-871` delete-before-embed intact; `delete_document` commits at `:1874` (profile) → unlink `:1885` → `:1901` (master); export files have 0 diff since `40f590e`; `tokenizer.json` under `models/embeddings/` not ignored (rc 1).
- Frontend: 32 `react-router-dom` importers, 3 `vi.mock('react-router-dom')` files; `tailwind-merge` 0 hits in owner-decisions; `openwiki/` = README only.

## 5. Not verified / UNMEASURED

- Every agent probe of regex behaviour (PARA recall regression, false alarms) was run outside the product module with copied patterns; re-run with `interpret_safety.py` before the owner decides.
- No full backend suite, vitest, Playwright or `npm audit` was run; every frontend advisory figure is quoted from a dated record (NPM-AUDIT-DRIFT: 10 on 2026-10-06).
- `core/external_runner.py` "dev bypass" Before-blocks (W-10 DP-4) accepted on the agent's reading of PR #32 lines `:180-185`, `:254-279`; not re-read by L0.
- ruff finding counts, coverage TOTAL, `agent_eval_gate.py` exit on Linux (GATE-14), FTS rebuild path (P7 N-02), HF cache state and `local_files_only` support in the 3.11 venv.
- Drift sections (4-7) were deliberately not produced for BLOCKED phases; W-2/W-7/W-8 carry a 5-anchor spot-check (§3b) only.
- Codex model IDs "6.1 sol" / "6-luna" are the owner's words; not confirmed against the `codex` CLI.
