# Wave 4 — L1-A report

**Last Updated:** 2026-10-08

Status: both phases are done and both PRs are open; neither is merged. Phase 1 (PROHIBITED-PARAPHRASE, measure-only, PR #51): **no measured pattern list meets the owner's three conditions, and none of the revised lists is offered for signing**; `src/backend/modules/interpret_safety.py` is not edited. Phase 2 (P5): 101 product lines migrated to `core.time.utcnow`, the badge timestamp converted (TIME-03), a CI lint added; both reviewers approve.

This copy (on the P5 branch) contains both phases. The copy on the Phase 1 branch contains Phase 1 only: when the second of the two PRs merges, resolve the add/add conflict on this file by taking this copy.

"L1" = run by the L1 orchestrator. "agent" = reported by a sub-agent; where L1 re-ran it, the row says so.

## Phase 1 — PROHIBITED-PARAPHRASE, measure-only

PR **https://github.com/BrooklynD23/HealthCentral/pull/51** · branch `test/prohibited-paraphrase-measure` · head `3d0d663` · base `origin/main@777adf5` · worktree `../hc-para-measure`

Plan: [`docs/plans/2026-10-04-PROHIBITED-PARAPHRASE.md`](../../../docs/plans/2026-10-04-PROHIBITED-PARAPHRASE.md) (section "Measure-first results").

### Gates used

| Gate | Row | Use |
|---|---|---|
| PARA-1-REDO ("Measure first") | `docs/capstone-report/owner-decisions-2026-09-27.md:66` | licenses this phase: corpora, in-memory measurement, a revised list for the owner |
| SLOT-RULE | `owner-decisions-2026-09-27.md:31` | collected slots rewritten in the commits that changed the count |
| PARA-1 (2026-10-07) | `:62` | superseded by PARA-1-REDO; not used |
| PARA-2 | unsigned | not needed |

### Task 0 (L1)

| Check | Output |
|---|---|
| `git merge-base --is-ancestor <c> origin/main` for `0bad019`, `ee5721d`, `930c678` | `0`, `0`, `0` |
| `git ls-files docs/plans/2026-10-04-PROHIBITED-PARAPHRASE.md` | the path |
| plan refresh check `git diff --quiet 90c502a origin/main -- <4 files>` | `0` |
| the plan's own scripts, extracted and re-run at `777adf5` | `13/42`, `13/77`; `plan_18` `37/42`, `0/77` (the plan's numbers reproduce) |
| collected at base | `1370 tests collected` |

### Commits

| # | Commit | Author |
|---|---|---|
| 1 | `e57b43c` test(safety): pin current prohibited patterns against a must-not-regress set | L2 (Sonnet); fixture written by L1 |
| 2 | `39b75d3` test(safety): add in-memory prohibited-pattern measurement script and corpora | L2; corpora by 2 independent agents |
| 3 | `7550088` test(safety): freeze revised candidate lists before the sealed split is measured | L1 |
| 4 | `9bd8967` test(safety): freeze revised_b before a third independent split is written | L1 |
| 5 | `fb811c5` test(safety): measurement script prints whole items and supports a third sealed split | L2 |
| 6 | `ec14d02` test(safety): add a third independently written held-out split | L1; corpus by a third independent agent |
| 7 | `8a7efee` docs(safety): record measure-first results and rewrite the PARA-1 sign-off | L1 |
| 8 | `6fd68cb` test(safety): harden the must-not-regress pin and pin every live pattern | L2; fixture rows by L1 from the code review |
| 9 | `23886bb` test(safety): measurement script gains --dedupe and --wrap | L2 |
| 10 | `7ed3118` docs(safety): correct the verdict after code review; no list meets the conditions | L1 |
| 11 | `9a68f9c` docs: Wave 4 L1-A report, Phase 1 | L1 |
| 12 | `82e35ad` test(safety): add the security review's lost-catch sentences and pin pattern reach | L2; fixture rows by the security reviewer |
| 13 | `edebe88` test(safety): measurement script gains --timing; no bytecode written | L2 |
| 14 | `7b61c4a` docs(safety): security-review corrections; no revised list is offered for signing | L1 |

15: `3d0d663` docs: Wave 4 L1-A report, Phase 1 after the security review (L1).

### Measured tables (L1, `HF_HUB_OFFLINE=1 ~/venvs/asclexis-311/bin/python scripts/measure_prohibited_patterns.py --final --final2 --markdown`, from `src/backend`)

Recall on must-block sets ("regr" = caught by the live list, missed by this list):

| List | in-sample | must-not-regress | held-out dev | held-out final | held-out final2 |
|---|---|---|---|---|---|
| `current` (live 11) | 13/42 (31.0 %) | 215/215 | 68/180 (37.8 %) | 68/191 (35.6 %) | 71/174 (40.8 %) |
| `plan_18` (the list signed 2026-10-07) | 37/42, regr 1 | 108/215, regr 107 | 76/180, regr 24 | 66/191 (34.6 %), regr 32 | 71/174 (40.8 %), regr 30 |
| `revised_min` | 16/42 | 169/215, regr 46 | 78/180 | 70/191 (36.6 %), regr 3 | 74/174 (42.5 %), regr 1 |
| `revised_a` | 42/42 | 171/215, regr 44 | 180/180 (in-sample) | **154/191 (80.6 %), regr 2** | **150/174 (86.2 %), regr 0** |
| `revised_b` | 42/42 | 170/215, regr 45 | 180/180 (in-sample) | 191/191 (in-sample) | **160/174 (92.0 %), regr 0** |

False positives on must-allow sets:

| List | in-sample (15) | product (62) | dev (175) | final (185) | final2 (171) |
|---|---|---|---|---|---|
| `current` | 6 | 7 | 10 | 22 | 13 |
| `plan_18` | 0 | 0 | 0 | 9 | 3 |
| `revised_min` | 0 | 0 | 0 | 2 | 2 |
| `revised_a` | 0 | 0 | 0 (in-sample) | **3** | **3** |
| `revised_b` | 0 | 0 | 0 (in-sample) | 0 (in-sample) | **2** |

Bold = out-of-sample for that list. With `--dedupe` (drops exact-text repeats across sets and the 21 sentences quoted in an author's report): `revised_a` 138/170 (81.2 %) and 139/163 (85.3 %); `revised_b` 149/163 (91.4 %), 2/169 false positives. With `--wrap` (a sentence before and after each text): unchanged, except `revised_b` on final 189/191.

### Verdict against the three conditions

| Condition | `plan_18` | `revised_a` | `revised_b` |
|---|---|---|---|
| (i) loses nothing on must-not-regress | fails (107 of 215 lost) | fails (at least 44 lost) | fails (at least 45 lost) |
| (ii) at least 85 % held-out recall, out-of-sample | fails (34.6 %, 40.8 %) | fails on final (80.6 %); 86.2 % on final2 | passes (92.0 %, one set) |
| (iii) 0 false positives on must-allow | fails (9, 3) | fails (3, 3) | fails (2 of 171) |

Best trade-offs found (none is offered for signing):
- **Recall:** `revised_b`, 92.0 % out-of-sample against 40.8 % for the live list, at the price of at least 45 lost catches, 2 false positives (the live list has 13 on the same 171 texts) and a run time of 3.98 s on one 2,500-character line (live: 0.01 s).
- **Precision only:** `revised_min` removes all 13 false positives on the 62 product texts and the plan's 15 sentences, adds almost no recall, and loses at least 46 catches.
- **The loss counts are floors.** L1's own 154 sentences showed 0 lost; the code review found 16; the security review then found 29 more for `revised_b`.

Run time (`scripts/measure_prohibited_patterns.py --timing`, seconds per whole-list pass; "it: " repeated to 1,250 and 2,500 characters, one-line lab table of 2,500):

| List | colons-1250 | colons-2500 | labtable-2500 |
|---|---|---|---|
| `current` | 0.00 | 0.01 | 0.00 |
| `plan_18` | 0.00 | 0.00 | 0.00 |
| `revised_min` | 0.07 | 0.19 | 0.05 |
| `revised_a` | 0.46 | 1.88 | 0.21 |
| `revised_b` | 0.91 | 3.98 | 0.58 |

One `revised_b` pattern (`D8b`) alone, L1: 0.56 s at 1,250 characters, 2.36 s at 2,500, 9.96 s at 5,000. The security reviewer measured 139.64 s at 19,999 (agent).
- **Why (i) and (iii) conflict:** live pattern 1 is "you have <any word>". Sparing "You have 3 open tasks" or "cannot show whether you have diabetes" needs a word list or a negation rule, and each also spares some diagnosis ("You have had a heart attack.", "I am not a doctor but you have diabetes.").

### How the out-of-sample claim was protected, and where it is weak

1. Three independent authors (Sonnet, Opus, Fable agents) wrote the held-out files from a neutral brief; each reported it did not open the patterns, the plan or the other files.
2. `revised_a` was committed (`7550088`) before `held_out_final` was first measured; `revised_b` was committed (`9bd8967`) before `held_out_final2` existed (`ec14d02`). `git diff 9bd8967 HEAD -- …/candidates.py` is empty.
3. Weak points: (a) the Opus author's report quoted 21 of its sentences and L1 read it before deriving `revised_a`; (b) `held_out_final.json` was in the repo before the `revised_a` freeze, so "not read" rests on L1's word; (c) L1 wrote the first 154 must-not-regress sentences and tuned against them, and the two reviews then found 16 and 29 more losses L1's set could not see; (d) `revised_b` has a single out-of-sample set by one author.

### Other commands and outputs

| Check | Who | Output |
|---|---|---|
| targeted `pytest tests/test_prohibited_patterns_regression.py tests/test_interpret_safety_adversarial.py tests/test_safe_chat_prohibited.py -p no:cacheprovider -q` (at `8a7efee`) | L1 | `15 passed, 1 warning in 7.21s` |
| `pytest tests/test_prohibited_patterns_regression.py -p no:cacheprovider -q` (at `7ed3118`; 4 tests at head, see the full suite) | L1 | `3 passed in 3.41s` |
| collect-only (head) | L2 (agent); L1 confirms by the full-suite count | `1374 tests collected` |
| full suite under flock, at `8a7efee` before the index was regenerated | L1 | `1 failed, 1371 passed` — `tests/test_docs_lint.py::test_docs_index_check_passes_on_real_repo`; cause: `docs/INDEX.md` not yet regenerated after the plan edit; fixed in `7ed3118` |
| full suite under flock, at `7ed3118` | L1 | `1373 passed, 54 warnings in 237.54s (0:03:57)`, rc=0 |
| full suite under flock, at `7b61c4a` (head before this report update) | L1 | `1374 passed, 54 warnings in 258.79s (0:04:18)`, rc=0 |
| break-it, HC-PARA-004: pattern 1 `\s+` → one space; pattern 3 without `indicates?`; pattern 4 `\d+` → `\d{1,3}`; pattern 6 `.*` → `.{0,20}`; no `re.IGNORECASE` | L2 (agent) | each: `1 failed, 3 deselected` |
| break-it: live list minus pattern 10, `pytest.main` in-process | L1 | `FAILED …test_hc_para_001…`, `1 failed, 1 passed`, rc=1; restored → pass |
| break-it: live list minus pattern 1; fixture owner list emptied; fixture trimmed to 150 | L2 (agent) | 001 fails; 002 fails; 002 fails |
| drop each live pattern 1…11 → fixture items missed (170-item set) | L1 | 84, 2, 2, 8, 14, 9, 9, 4, 12, 9, 5 (every pattern is pinned; HC-PARA-003) |
| `git diff origin/main...HEAD --name-only \| grep -c "src/backend/modules/\|src/backend/api/"` | L1 | `0` |
| `python3 scripts/generate_docs_index.py && python3 scripts/docs_lint.py --link-graph` | L1 | `Wrote docs/INDEX.md (1395 lines)`, `Docs lint passed.`, `Link graph written to docs/_link_graph.json` |

Collected-count delta: **1370 → 1374 (+4)**: HC-PARA-001, 002, 003, 004. Slots rewritten at `CLAUDE.md:30`, `:35` and `AGENT.md:76` in `e57b43c` (1372), `6fd68cb` (1373) and `82e35ad` (1374).

### Reviews

| Reviewer | Verdict | What was fixed |
|---|---|---|
| code-reviewer (Opus), round 1 at `8a7efee` | REQUEST CHANGES, 0 critical, 2 high, 7 medium | H1: 16 sentences the live list catches and `revised_b` misses → added to the fixture, verdict row (i) corrected to "fails", sign-off rewritten (`6fd68cb`, `7ed3118`). H2: test 002 read the owner sentences from the fixture it checks → hard-coded in the test, exact per-group counts pinned, new HC-PARA-003 (`6fd68cb`). M1 (limits of the git evidence), M2 (duplicates: `--dedupe`), M3 (the 21 quoted sentences are now listed in the fixture and removable by command), M4-M6 (limits and wording) → `23886bb`, `7ed3118` |
| security-reviewer (Opus) at `7ed3118` | REQUEST CHANGES (docs only), 0 critical, 2 high, 2 medium, 4 low. No safety guarantee changed; the script writes nothing and reaches no network (audit hook, `unshare -rn`); fixtures are synthetic | H1: "16 losses" was a floor; its 45 probe sentences (29 lost by `revised_b`) are now in the fixture and the plan says "at least" (`82e35ad`, `7b61c4a`). H2: the plan's run-time limit was wrong; growth is quadratic; L1 reproduced it, the plan's limit 4 is rewritten, `--timing` added, and no revised list is offered for signing. M1: the sign-off now says what would have to happen to HC-PARA-001 if a losing list were signed. M2: HC-PARA-004 pins 5 of the 7 surviving weakenings (the other two, "if you have" and "you have 3", are the open owner question). L1-L3: bytecode flag moved; stale execution steps and the stop gate rewritten. L4 (pass-count wording) not touched: owner item AGENT-PASS-LINE |

Both reviewers re-ran the measurement and found 0 mismatches against the plan's tables at the commit they reviewed. No third review round was run on the last two commits (`82e35ad`, `edebe88`, `7b61c4a`): they add pinned sentences, one test, one script mode and plan text.

### Findings not fixed (owner items)

| # | Finding | Evidence |
|---|---|---|
| 1 | The live list catches 35.6 % to 40.8 % of independently written must-block sentences | tables above; `interpret_safety.py:49-68` |
| 2 | The live list flags 13 of the product's own 77 texts (3 agent draft sentences, 7 seeded KB fields, 3 education sentences) | plan "Measured baseline"; `modules/agent/nodes/draft.py:155`, `:193`, `:249` |
| 3 | No regex list measured here meets "0 lost, 85 %, 0 false positives", and the broad lists are quadratic in line length | verdict and run-time tables |
| 3a | The pin tests do not cover whole answers, must-allow text, category names, or `rag.py`'s own compiled copy (dropping `re.IGNORECASE` at `modules/rag.py:178-181` would not be caught by HC-PARA) | security review Q2 |
| 4 | `revised_b` adds false positives on app-instruction text ("Add your medications to your profile …", "Your data will never leave this device.") that no must-allow set contains | code review M4; plan "residual false positives" |
| 5 | The default chat path (agent) does not read these patterns | `modules/agent/settings.py:19`; PARA-2 unsigned |
| 6 | `filter_prohibited_content` has no product caller | `interpret_safety.py:213`; one test |
| 7 | Real model output is UNMEASURED | no captured answers in the repo |
| 8 | `CLAUDE.md:31` still says "all 1288 pass" beside 1373 collected; on this machine 1373 pass | AGENT-PASS-LINE owner item; not touched (slot rule covers the collected number only) |

### The sign-off question for the owner

> **PARA-1.** No measured list meets the three conditions you set (0 lost on must-not-regress, at least 85 % held-out recall, 0 false positives), and none of the revised lists is offered for signing: each loses catches the live list makes (at least 44 to 46 known sentences, for example "You have multiple sclerosis." and "You have had a heart attack."), and the two broad lists take seconds on one long line. Choose one:
> - **A. One more round, then decide (recommended).** Keep the live list for now. The next list must lose 0 of the 215 pinned sentences, meet a run-time bound (proposed: under 0.1 s on each timing input, also at 5,000 characters), and be measured on a fourth independent split that includes app-instruction text.
> - **B. Stop trying to do this with patterns.** Keep the live list as a floor and move the recall problem to another layer (PARA-2, the agent draft path, or a classifier step). That needs its own plan.
> - **C. No pattern edit, no further work.** The live list stays at 35.6 % to 40.8 % held-out recall, with false positives on 7 of the product's own 62 texts.

## Phase 2 — P5, `datetime.utcnow` → `core.time.utcnow`

PR **https://github.com/BrooklynD23/HealthCentral/pull/54** · branch `fix/p5-utcnow-migration` · base `origin/main@777adf5` · worktree `../hc-p5`

Plan: [`audit/2026-09-25/plans/05-utcnow-migration.md`](../plans/05-utcnow-migration.md) (amended in the first commit; execution record at its end).

### Gates used

| Gate | Row | Use |
|---|---|---|
| D13 | `docs/capstone-report/owner-decisions-2026-09-27.md:23` | the 6 swap lines in the auth file `api/profiles.py` |
| P5-SCOPE ("Include TIME-03") | `:67` | `modules/badge_evaluator.py:84` → `utcnow()`; the dose-log `earned_at` string changes |
| P5-IMPORT ("Yes, remove it") | `:74` | deletion of `from datetime import datetime` at `api/profiles.py:13` |
| SLOT-RULE | `:31` | collected slots rewritten in the two commits that added tests |
| CI-SEED | unsigned | not used: the lint's red state is proved locally only |

### Task 0 (L1)

| Check | Output |
|---|---|
| `git merge-base --is-ancestor <c> origin/main` for `cff3827` (P2), `6b4dd84` (P4-core), `2f0cb6f` (W-6), `7b2ff1f`, `692fdf3` (P1) | `0` each |
| `git ls-files audit/2026-09-25/plans/05-utcnow-migration.md` | the path |
| `ls scripts \| grep -c time_source_lint` (not already done) | `0` |
| product lines / files with `datetime.utcnow` | `101` / `30` (the plan's enumeration, file by file) |
| test lines | 20 in 8 files (18 in 7 files plus 2 string literals in `test_profile_recovery.py`) |
| collected at base | `1370 tests collected` |
| `grep -n "datetime" src/backend/api/profiles.py` at base | line 13 and the 6 swap lines only, so P5-IMPORT applies |

### Plan amendments (commit `f12db77`, L1; each verified against the code first)

| # | Amendment | Evidence |
|---|---|---|
| 1 | TIME-03 into scope as Task 12b; the "serialization unchanged" constraint now names the one accepted change | owner row P5-SCOPE; `api/medications.py:285` |
| 2 | Import rule matches P5-IMPORT; the six files whose `datetime` import becomes unused are named | `grep -n datetime` on each |
| 3 | The lint is an AST scan | the plan's line-regex matched the docstring at `src/backend/core/time.py:18`; the AST version, run on the unmigrated tree, reported 101 lines in 30 files and nothing in `core/time.py` |
| 4 | CI step name quoted; placed after `Repo hygiene check` | unquoted `Lint: …` is a YAML mapping error; `ci.yml:30-31` |
| 5 | Seeded-gate command uses real paths | the old one `cd /tmp` then used repo-relative paths and a `<repo>` placeholder |
| 6 | Moved line numbers; Task 1 = 13 files; Task 12 = 7 files / 18 sites | re-measured at `777adf5` |
| 7 | HC-TIME-005 added (D13: "tests must show identical serialization") | no test in the first version looked at a response |
| 8 | Task 14 Step 2 third grep: three lines, not two (corrected after execution) | `tests/test_time_source.py:4` is a docstring the plan itself adds |

### Commits

| # | Commit | Author |
|---|---|---|
| 1 | `f12db77` docs(p5): amend the utcnow plan for P5-SCOPE, P5-IMPORT and the Codex plan review | L1 |
| 2 | `9e6bea3` test(time): pin naive-UTC semantics of core.time.utcnow | L2 (Sonnet) |
| 3 | `2fdd5f1` fix(models): use core.time.utcnow for all column defaults | L2 |
| 4 | `950a821` fix(api): use core.time.utcnow in documents routes | L2 |
| 5 | `b2a4e8c` fix(api): use core.time.utcnow for verification timestamps | L2 |
| 6 | `2c47f22` fix(api): use core.time.utcnow in notification routes | L2 |
| 7 | `da0d383` fix(api): finish core.time.utcnow migration in profiles/model_settings | L2 |
| 8 | `bdce42f` fix(modules): use core.time.utcnow in notification scheduler | L2 |
| 9 | `55e9be1` fix(modules): use core.time.utcnow in adherence patterns | L2 |
| 10 | `48eeb72` fix(modules): use core.time.utcnow in platform notifications | L2 |
| 11 | `09a640f` fix(agent): use core.time.utcnow for step timestamps and trend cutoff | L2 |
| 12 | `f00e69f` fix(modules): use core.time.utcnow at export/ingest serialization sites | L2 |
| 13 | `7b00902` fix(modules): use core.time.utcnow in hardware detection and model selector | L2 |
| 14 | `2d1b279` test: use core.time.utcnow in remaining test helpers | L2 |
| 15 | `1a7b33e` fix(gamification): store and return the badge timestamp as naive UTC | L2 |
| 16 | `d4b70dd` ci: gate src/backend on core.time.utcnow helper | L2 |

| 17 | `41dcb35` ci: time-source lint fails when it scanned nothing; exclude only top-level tests | L2 |

A last commit (L1) carries the plan's execution record, the session note and this report.

### Commands and outputs (L1 unless marked; D9 venv Python 3.11.16, `HF_HUB_OFFLINE=1`)

| Check | Output |
|---|---|
| `grep -rn "datetime\.utcnow" src/backend --include="*.py" \| grep -v "src/backend/tests/" \| wc -l` | `0` (was `101`) |
| `grep -rn "datetime\.utcfromtimestamp" src/backend --include="*.py" \| grep -v "src/backend/tests/"` | one line: the docstring at `src/backend/core/time.py:18` |
| `grep -rn "datetime\.utcnow" src/backend/tests --include="*.py"` | three lines: `test_profile_recovery.py:344`, `:350` (literals), `test_time_source.py:4` (docstring) |
| `python3 scripts/time_source_lint.py; echo exit=$?` on the clean tree (at `d4b70dd`) | `time_source_lint passed: no datetime.utcnow/utcfromtimestamp in src/backend product code.` `exit=0` |
| the same at `41dcb35` | `time_source_lint passed: no datetime.utcnow/utcfromtimestamp in 173 src/backend product files.` `exit=0`; seeded probe → `exit=1` (L1); a probe under `src/backend/modules/tests/` → `exit=1`, an empty scan root → `time_source_lint ERROR: scanned 0 .py files …` `exit=1` (L2, agent) |
| at `d4b70dd`, with `src/backend/_planted_lint_probe.py` seeded (`x = datetime.utcnow()`) | `src/backend/_planted_lint_probe.py:2: x = datetime.utcnow()` `exit=1`; probe removed |
| break-it: `models/audit.py` swap reverted | `src/backend/models/audit.py:63: DateTime, default=datetime.utcnow, nullable=False, index=True` `exit=1`; restored → `exit=0` |
| `python -c "import yaml; …ci.yml… ['docs-lint']['steps']"` | `[None, 'Set up Python', 'Run docs lint', 'Check generated docs freshness', 'Lint feature inventory', 'Repo hygiene check', 'Lint: deprecated datetime helpers banned in backend']` |
| every changed line that is not a pure `datetime.utcnow` → `utcnow` swap (script over `git diff -U0`) | only: 29 added `from core.time import utcnow`; 6 deleted `from datetime import datetime` (the named files); `badge_evaluator.py:84`; blank lines beside the import in 5 files; the new tests. 120 pure swap lines |
| `git diff origin/main...HEAD -- src/backend/api/profiles.py` | 7 changed lines: 6 swaps (3 in `create_profile`, `login`, `unlock_profile`, `change_password`) and the deleted import |
| ruff `F401,F811,F821` and `I` on the changed files, head vs base | 35 vs 35 and 44 vs 44; no new finding |
| `pytest tests/test_time_source.py tests/test_medications_dose_logging.py -p no:cacheprovider -q` | `8 passed in 7.23s` |
| Task 12b RED (L2, agent) | `2 failed, 6 passed`; HC-TIME-007: `AssertionError: 2026-10-08T22:13:57.693517+00:00` |
| break-it: `modules.badge_evaluator.utcnow` patched to an aware clock, in-process | `FAILED …test_hc_time_006…`, `FAILED …test_hc_time_007…`, `2 failed, 6 deselected`, rc=1 |
| collect-only | `1377 tests collected` |
| full suite under flock at `d4b70dd` | `1377 passed, 66 warnings in 226.47s (0:03:46)`, rc=0 |
| `python -c "from main import app; print('boot ok')"` | `boot ok` |
| `timeout 600 python scripts/agent_eval_gate.py; echo rc=$?` (GATE-14) | `All 74 golden cases passed.` `Agent eval gate: PASS` `rc=0` (it exited by itself on Linux 3.11) |
| frontend on Windows, `npm ci; npx vitest run`, before any code change (at `f12db77`) | `Test Files 34 passed (34)`, `Tests 195 passed (195)` |
| frontend on Windows at `d4b70dd`, 4 full runs | runs 1 and 2: `1 failed \| 194 passed` (FE-BKUP-001 in `BackupRestoreFlow.test.tsx`, while two review agents were running tests); that file alone: `4 passed`; run 4: `34 passed (34)`, `195 passed (195)`. Run 3's summary line was not captured. No frontend file is in the diff (`git diff origin/main...HEAD --name-only \| grep -c src/frontend` → `0`) |

The 66 warnings (base runs: 54): 12 `PytestUnhandledThreadExceptionWarning` (aiosqlite "Event loop is closed") in `tests/agent/test_s5_cutover_cache.py`. L1 ran `tests/agent/` three times per tree: the P5 tree printed 14, 14 and 4 such lines; a tree with `origin/main` product code printed 0, 0 and 14. So the warning also occurs without this diff; it is teardown timing, not P5.

Collected-count delta: **1370 → 1377 (+7)**: HC-TIME-001…005 (`9e6bea3`, slots → 1375) and HC-TIME-006, 007 (`1a7b33e`, slots → 1377).

### TIME-03 trace (L1, before the change; both reviewers re-derived it)

| Reader / writer of the badge timestamp | Effect of the naive value |
|---|---|
| `_to_local_date(now, tz)`, `badge_evaluator.py:86` | none: a naive value is read as UTC (`:53-54`) |
| `EarnedBadge.earned_at`, naive `DateTime` (`models/gamification.py:64-68`, migration `003:70`) | stored text identical (the reviewers checked: both forms store `2026-03-04 08:00:00.123456`) |
| `BadgeInfo.from_result`, `api/medications.py:285` | **the accepted change:** `…123456+00:00` → `…123456` |
| `api/gamification.py:102` | unchanged; it already returned the naive form read back from the database |
| comparisons with another datetime | none |
| frontend | `BadgeInfo.earned_at` (`services/types.ts:454`) has no reader; `BadgeToast.tsx` shows icon and name; `AchievementsWidget.tsx:43,45` reads `BadgeStatus` from `/gamification/badges` |

### Reviews

| Reviewer | Verdict | What was fixed |
|---|---|---|
| code-reviewer (Opus) at `d4b70dd` | APPROVE; 0 critical, 0 high, 0 medium, 4 low | L1 (lint misses aliased imports) recorded as a known limit in the plan; L2 (HC-TIME-001…005 pass before and after) stated in the PR; L3, L4 no change |
| security-reviewer (Opus) at `d4b70dd` | APPROVE; 0 critical, 0 high, 0 medium, 3 low. Auth diff is exactly 7 lines; no swapped value feeds a security decision (lockout uses `time.time()`, token revocation `session.expires_at.timestamp()`); no aware/naive pairing; export formats byte-identical; no log line added | L1 (lint passes when it scanned nothing) and L2 (`tests` excluded at any depth) fixed in a follow-up commit; L3 (aliases) recorded as a known limit |

### Findings not fixed (owner items)

| # | Finding | Evidence |
|---|---|---|
| 1 | `AchievementsWidget.tsx:45` parses an offset-less timestamp with `new Date(...)`, which browsers read as local time; a badge earned near midnight UTC can show the neighbouring day. Pre-existing; not changed by P5 | `src/frontend/src/components/medication-coach/AchievementsWidget.tsx:45`; `api/gamification.py:102` |
| 2 | The other aware-datetime sites stay as they are (TIME-03 remainder) | `core/auth.py:73,144,207`, `core/security.py:136`, `core/token_revocation.py:51`, `api/export.py:949,1005`, `api/model_settings.py:344`, `api/gamification.py:148`, `api/medications.py:84` |
| 3 | The lint does not see an aliased import (`from datetime import datetime as dt; dt.utcnow()`) or `getattr` | both reviews; no such alias exists in product code today |
| 4 | HC-TIME-001…005 pass before and after the migration; a missed swap is caught by the lint only. HC-TIME-005 (the D13 serialization evidence) pins `ProfileResponse.from_model`, not the HTTP routes | plan Task 0; both reviews |
| 5 | `docs/architecture/ci-and-quality-gates.md:17` does not list the new `docs-lint` step | W-11a PR-3 Task 9 owns that file |
| 6 | Pass-count sentences are stale: `CLAUDE.md:31` "all 1288 pass", `AGENT.md:76` "1269 pass in CI"; this machine: 1377 passed | AGENT-PASS-LINE; the slot rule covers the collected number only |
| 7 | FE-BKUP-001 (`src/frontend/src/__tests__/BackupRestoreFlow.test.tsx`) failed in 2 of 4 full vitest runs on a loaded machine and passes alone | frontend row above |
| 8 | `tests/agent/test_s5_cutover_cache.py` intermittently prints aiosqlite "Event loop is closed" thread warnings in longer runs, with and without this diff | warnings paragraph above |
| 9 | The lint's red state in real CI is unproved (CI-SEED unsigned) | local proof only |
| 10 | The commit subject of `1a7b33e` says "store … as naive UTC"; the stored value did not change, only the in-memory value and the response string | reviewers' SQLite check |

### Merge-order notes (both phases)

- **Count slots** (`CLAUDE.md:30`, `:35`, `AGENT.md:76`): Phase 1 writes 1374, P5 writes 1377, both from 1370. Whichever merges second merges `origin/main`, re-measures and rewrites: the number after both is **1381** (1370 + 4 + 7), to be measured, not assumed. Any PR from the other L1 that changes collection shifts this again.
- **This report file**: add/add conflict between the two branches; take the P5 copy.
- **`docs/features/TASK_LIST.md`**: P5 adds a Session Note at the top; other open PRs that add one conflict there (keep both, newest first).
- **`docs/INDEX.md`, `docs/_link_graph.json`**: regenerated on each branch; regenerate after the second merge.
- **`.github/workflows/ci.yml`**: P5 appends one step to `docs-lint`; order P5 → W-4 → W-11a PR-3 → W-8 (pack §5).
- **Product files P5 touches that later phases also edit** (P5 first): `api/profiles.py` (P7, W-11a PR-1, G-C1), `modules/export.py` (W-2), `api/observations.py` (W-3), `api/interpretations.py`, `modules/model_selector.py` (W-7), `api/documents.py` (W-8), `models/document_category.py` (P6).
- Phase 1 touches no product file, so the two PRs do not overlap in code and can merge in either order.

Next action: the owner answers PARA-1 on PR #51, and reviews the 7-line `api/profiles.py` diff on PR #54.
