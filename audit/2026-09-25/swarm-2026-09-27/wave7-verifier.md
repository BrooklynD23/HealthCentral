# Wave 7 verifier report (7-verifier, 2026-09-28)

Result: 6 of 7 queued items fixed, 1 needed no change (HC-VER: no selector collides), and 1 was left as the brief instructs (openwiki: the target exists). The sweep found 14 more inconsistencies and fixed all 14. 20 files changed, nothing committed, and no gate was signed. `docs_lint` passes. The link check finds 1 broken link (the openwiki one, left on purpose).

## 1. Queued items

| # | Item | Result | Evidence / why |
|---|---|---|---|
| 1 | HC-VER-001 prefix vs B's HC-VERIFY-00x | **not renamed (no collision)** | Every selector is anchored: W03 `-k hc_ver_00N`, `git grep -nE "HC-VER-[0-9]\|hc_ver_0\|HC-VER-FE"`; W08 `:227` and W10 `:417` use `"HC-VER-001"`. B's names are `test_hc_verify_00N_*` (`B:test_verify_model_repos.py:39-89`). Neither `hc_ver_0` nor `HC-VER-0` is a substring of `hc_verify_0` or `HC-VERIFY-0`. `git grep -nE "HC-VER-[0-9]\|hc_ver_"` returns 0 hits on main, A and B. The only bare `HC-VER` is prose (senior plan `:846`). W03 `:42` already says to anchor. A rename would touch 4 files and add 0 safety |
| 2 | Re-anchor implementation-program line citations | **fixed, 21 citations in 9 files** | The program moved (+211/−50). New anchors, each checked with `sed -n`: P3 `:274`, acceptance `:288`, P4 `:292-310`, data-privacy bullet `:302`, hipaa `:303`, D11 `:304`, owned files `:305`, sign-off `:311`, P8 `:369-381`, G-A1 `:389`, G-B5 `:396`, G-C1…5 `:398-402`, `api/profiles.py` order `:137`, `modules/export.py` order `:143` (quote updated), data-privacy order `:154`, graph `:45-128`, P0-D edge `:120`. Historical findings keep the old line, marked `@5d56557`, next to the new one |
| 3 | Plan 05 banner "7 aware sites in 6 files" + TIME-03 | **fixed** | Re-ran `git grep -nE '(dt_)?timezone\.utc' 40f590e -- 'src/backend/*.py' ':!src/backend/tests' ':!src/backend/core/time.py'`: **12 lines, 8 files**. The plain form is 7 sites in **5** files. Persistence re-read: `badge_evaluator.py:84` → `earned_at=now` `:101` → `EarnedBadge` `:157-163`, a naive `DateTime` column (`models/gamification.py:64-68`), reached from `api/medications.py:1000`. The banner is fixed. The program TIME-03 row said "No persisted aware value found", which is false. It now carries the persistence chain. Proposed: add the `badge_evaluator.py:84` site to P5 scope, owner decides. `core/auth.py` and `core/security.py` stay ask-first |
| 4 | LOCAL-07 `data-privacy.md:196-197` | **recorded as a program owner item (not added to W-10 scope)** | Re-verified `rag.py:1256-1267` @main: the whole composed prompt goes to the runner. W-10 §1.4 #8 explicitly excludes it ("no decision covers"). W-10's round 4 is final, so widening its scope would bypass review. P04 §1 #2 bars P4 from `data-privacy.md`. W-10 F-2 said "P4 addendum", which loops back to W-10. Fix: a new LOCAL-07 row in "Program owner items" (proposed home: a W-10 addendum). Matrix LOCAL-07 "Planned by" and W-10 F-2 now point to it |
| 5 | Matrix GATE-04 `\|\| true` | **fixed, plus 4 more of the same class** | A cell-count check (GFM pipe split, fence-aware) found 5 broken rows: matrix `:148` (10 vs 8), claims `:44` (6 vs 4), overview `:170` (5 vs 3), W10 `:124` (4 vs 2), W11a `:1892` (3 vs 2). All pipes are escaped now. Re-run: 0 mismatches |
| 6 | 6B stale-text list | **fixed, each fix citing its owner-decision line** | See the §1a table |
| 7 | plan 04 → `openwiki/README.md` | **left, reported** | `openwiki/README.md` exists on main, A, B and HEAD. The broken link is plan 04 `:600`: quoted `AGENT.md` text whose relative path resolves from `audit/2026-09-25/plans/`. The `:594` link is inside a fence. The brief says to leave the link when the target exists |

### 1a. Item 6: stale owner-gated text and the decision each fix cites

| Location | Was | Now | Decision line quoted |
|---|---|---|---|
| contract reconciled table: Export redaction | "Owner-gated" | D3 decided | `owner-decisions:15` "Redact doctor summary only" |
| contract reconciled table: Verified-only | "Owner-gated" | D4 decided | `:16` "Label, exclude from RAG" |
| contract reconciled table: HIPAA | "Conditional; legal review" | D10 decided (posture, not legal status) | `:24` "Treat as HIPAA-aligned" |
| contract reconciled table: External runner | "Owner-gated deviation" | D12 decided | `:22` "Keep, harden" |
| contract C-LOCAL-1 exceptions bullet | "owner-gated" | owner-approved D12, not yet in CLAUDE.md | `:22` |
| contract C-REDACT-2 "(OWNER-GATED, not approved here)" | — | D12: remove the dev bypass; break-glass only with audit + UI warning; neither done yet | `:22` |
| contract C-LOCAL-2 Owner line | "Owner decides whether implicit … acceptable" | D8 + D8-delivery decided; EMB-REV unsigned | `:21` "Bundle the model", `:26` "Script + offline load" |
| matrix GATED-08 | "none" | D3 + D4 decided; P0-D-MOOT unsigned | `:15-16` |
| overview `:87` `logs/asclexis.log` | "UNVERIFIED" | false (matrix AUD-05) | not an owner item; factual. Re-checked: `log_file_path` is used only at `core/database.py:87` (mkdir); no `FileHandler` or `dictConfig` @main/A/B |
| overview §13 `.claude/agents` row | "owner-gated (§21 Q2)" | D1 decided | `:17-18` "A: build real agents" / "All 5" |
| overview §13 export/verification scope | "owner-gated" | D3 + D4 decided | `:15-16` |

## 2. Consistency findings (Part 2)

| File:line | Issue | Fixed? |
|---|---|---|
| program W-plans P4-core row | **D4-EXPORTS** (P04 OG-2) missing from the program register | yes, added to stop gates |
| program RTN row | **RTN Q6** missing from the program | yes, added (proposed default "do not enable", from spec `:165`) |
| program W-10 row | GOV-BG default and wording not in the program (6D handoff) | yes: proposed default "include"; the "only bypass" wording goes in only when signed |
| W07 `:156` | ci.yml order "P1 → P5 → G-B3/G-B4 (W-11a)" is wrong: G-B3 is W-6/W-7, and W-4 and W-8 are missing | yes → P1 → P5 → W-4 → W-11a PR-3 → W-8 |
| W06 `:176` | `core/config.py` order has no S-1 | yes → P1 → S-1 → P4 (N7) → W-8 |
| W08 `:164` | `core/config.py` order has "→ W-6 (if it edits config)", but W-6 §4.2 lists the file read-only | yes, W-6 removed |
| W11a `:180` | ci.yml order ends at W-11a (no → W-8) | yes, → W-8 appended |
| capstone README `:23`, report-outline `:28` | "62 rows" | yes → 73. My own recount: 73 rows, 73 unique IDs: 4 enforced · 18 tested · 4 implemented · 15 partial · 20 gap · 9 contradicted · 2 owner-gated · 1 unknown, matching matrix `:33` |
| senior plan `:56`, `:111` (M4), `:531` (S172), `:558` (O10) | "62 rows" (the S172 text would ship the stale number) | yes → 73, with 62 kept as the 2026-09-27 figure |
| senior plan `:177` (F18) | "S-1 and the W-plans are not drawn" is false: the graph now draws them | yes |
| contract C-MIG-3, C-SCHED-2; reconciled FK and Serena rows; matrix MIG-03, GATED-07; overview `:114`, FK and notifications rows; program D8 row + W08 `:86` quote | still "owner-gated" or "delivery open" after **D5, D6, D2, D4, D8-delivery** | yes, each citing `owner-decisions:14`, `:13`, `:19`, `:16`, `:26` |
| program "Also unowned" | PRIV-06 remainder (`api/profiles.py:328` logs the display name at INFO, main = B) had no home (6E handoff) | yes, registered as unowned; owner decides |
| gate IDs (2a) | all 22 IDs found; none is signed or approved unconditionally. Every "signed" hit is conditional (W-6 SLOT-RULE branches, W-10 GOV-BG variants) | no issue |
| shared files (2b) | rag.py W-5 → W-3 → W-8 agrees in W03 `:177`, W05 `:185`, W08 `:167` and the program. ci-and-quality-gates.md agrees in P04 `:170`, W08 `:170`, W11a `:181` and the program `:140` | no issue |
| numbers (2c) | 165/28 and 28/5 are consistent. A+B 179/31 = matrix `:147` = W11a `:1816`. Every 1269 is labelled "B `AGENT.md:76` stale". 91,578,415 appears in 8 places, all equal. The remaining "155/25" mentions are quoted claims or dated records | no issue |
| claims (2d) | 0 unconditional "signed / merged / passes" claims (scan for was/now/already + signed/merged/passing, filtered for conditionals and reviewed by hand) | no issue |

## 3. Files changed (20)

1. `docs/capstone-report/implementation-program.md`: TIME-03, new LOCAL-07 row, D4-EXPORTS, RTN Q6, GOV-BG, D8 row, PRIV-06 remainder
2. `docs/capstone-report/specs-compliance-matrix.md`: GATE-04 pipes, LOCAL-07 Planned-by, MIG-03, GATED-07, GATED-08
3. `docs/capstone-report/architecture-engineering-contract.md`: C-LOCAL-1, C-LOCAL-2, C-REDACT-2, C-MIG-3, C-SCHED-2, 6 reconciled rows
4. `docs/capstone-report/architecture-overview.md`: `:87`, `:114`, `:170`, §13 rows ×4
5. `docs/capstone-report/claims-ledger.md`: `:44` pipes
6. `docs/capstone-report/README.md`: `:23` row count
7. `docs/capstone-report/report-outline.md`: `:28` row count
8. `audit/2026-09-25/plans/05-utcnow-migration.md`: banner item 2
9. `docs/plans/2026-09-27-P04-doc-drift-sweep-amendment.md`: 6 re-anchors
10. `docs/plans/2026-09-27-P08-gated-packet-hipaa-aligned-amendment.md`: 2 re-anchors
11. `docs/plans/2026-09-27-W01-harness-agents-branch-a.md`: `:64` re-anchor
12. `docs/plans/2026-09-27-W02-doctor-summary-redaction.md`: 5 re-anchors
13. `docs/plans/2026-09-27-W04-legacy-abstain-and-eval-gate.md`: `:61` re-anchor
14. `docs/plans/2026-09-27-W06-external-runner-hardening.md`: `:176` config order
15. `docs/plans/2026-09-27-W07-tiered-interpretation-via-modelrunner.md`: `:156` ci order
16. `docs/plans/2026-09-27-W08-bundled-embedding-model.md`: `:86` quote, `:164` config order
17. `docs/plans/2026-09-27-W10-governance-invariant-amendments.md`: F-2 routing, F-5 re-anchor, `:124` pipes
18. `docs/plans/2026-09-27-W11a-test-and-gate-hardening.md`: `:180` ci order, `:1892` pipe
19. `docs/plans/2026-09-27-W11b-roadmap-items-gc1-gc4.md`: `:156`, `:254` re-anchors
20. `docs/plans/2026-09-27-senior-report-showcase-plan.md`: F18, the 62→73 rows, `:177` anchor

Plus this report. The `.serena/project.yml` modification was there before this wave and is not mine.

## 4. Remaining owner decisions (deduped; all unsigned)

| Gate | What the owner decides | Recommended default in the docs |
|---|---|---|
| P0-B2 | Commit the plan set on the docs branch; include or exclude the 16th file (senior-report plan) | none stated; must be named explicitly |
| D9-SRC | Source of the 3.11 interpreter (uv CPython 3.11.16; no `python3.11` on PATH) | none stated |
| P1-DRIFT | Reword the drift token so `harness_drift_check` exits 0 after P1 | none stated |
| SLOT-RULE | Collected-count slots move in the same commit (ground rule 8, incl. the W-6 carve-out) | proposed rule; unsigned |
| W4-EXPEDITE | Land W-4 before P4/P5 | optional; "no plan recommends it" |
| P7-ROUTE | P7 edits the `/profiles/test/reset` route in auth-adjacent `api/profiles.py` | yes |
| GOV-BG | W-10 C-2/DP-4 break-glass "only bypass" wording (W-6 Q2) | "include" |
| GOV-D11 | `CLAUDE.md:62` citation wording via W-10 Q1 | none; unsigned → `:62` unchanged |
| BG-REACH | W-6 Q1 (break-glass reachability) | see W-6 §11 |
| P8-B2-ORDER | P8 Brief 2 signed before P4 N9 (`hipaa-controls.md:169`) | order as stated |
| SQL-ECHO (S1-A, S1-B) | `sql_echo` setting; `core/profile_database.py` line (ask-first) | none; owner signs each |
| EXPORT-QUESTIONS | W-2 O-4 / P08 R11 export questions | see W-2 O-4 |
| D4-EXPORTS | Exports carry unverified rows; D4 does not cover exports (P04 OG-2) | P4 only documents it |
| VERIFIED-FALLBACK | W-3 O-1 with W-8 Q-FC: the knowledge fallback cites verified values only | O-1 = yes, signed before W-8 merges |
| EMB-REV | Pin `all-MiniLM-L6-v2@1110a243…` | the pin in W-8 |
| CI-SEED | One approval for throwaway seeded draft PRs (W-4, W-11a PR-3) | closed unmerged |
| P0-D-MOOT | P0-D brief is moot after D3/D4 | moot (W-2 S-5) |
| RTN Q6 | Enable the routine if the session can push | do not enable |
| Program owner items (no plan) | INTERP-UNVERIFIED, MSG-UNVERIFIED, AUD-INTERP (W-7 OG-3), C-LLM-2 remainder, RL-EXPORTS (new ask-first plan), GATE-14 (W-11a proposed), TIME-03 (P5 scope for `badge_evaluator.py`), **LOCAL-07 (W-10 addendum)**, KEY-08, GATE-12 (W-11a proposed), PRIV-06 display-name log (S-1 addendum or leave) | as in program "Program owner items" |

Open for owner acceptance (ledger `:60`): the round-4 fixes for W-1, W-2 and P08 BLOCKERs, the W-8 MAJOR, and the W-10 r4 fix were not re-reviewed.

## 5. Verification output

```
$ python3 scripts/docs_lint.py; echo "rc=$?"
Docs lint passed.
rc=0

$ python3 <fence-aware relative-link check over docs/capstone-report/*.md, docs/plans/2026-09-27-*.md, audit/2026-09-25/plans/*.md, handoff>
audit/2026-09-25/plans/04-doc-drift-sweep.md:600: openwiki/README.md
links checked=283 broken=1 files=34

$ python3 cells.py <same 34 files>   # GFM table cell-count check
(no output) rc=0

$ git diff --check -- . ':!.serena'
check_rc=0
```

Next action: the orchestrator runs `git diff --stat -- docs/ audit/2026-09-25/plans audit/2026-09-25/swarm-2026-09-27/wave7-verifier.md` (expect 20 files + this report) and commits.
