# Wave 4 — L1-A report

**Last Updated:** 2026-10-08

Status: Phase 1 (PROHIBITED-PARAPHRASE, measure-only) is done and its PR is open. **No measured pattern list meets the owner's three conditions, and none of the revised lists is offered for signing** (lost catches; quadratic regex run time found by the security review). `src/backend/modules/interpret_safety.py` is not edited. Phase 2 (P5) is reported in the copy of this file on the P5 branch.

"L1" = run by the L1 orchestrator. "agent" = reported by a sub-agent; where L1 re-ran it, the row says so.

## Phase 1 — PROHIBITED-PARAPHRASE, measure-only

PR: see the PR that carries this file · branch `test/prohibited-paraphrase-measure` · base `origin/main@777adf5` · worktree `../hc-para-measure`

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

A last commit updates this report.

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

### Merge-order notes

- `CLAUDE.md:30`, `:35` and `AGENT.md:76`: this PR writes 1374. P5 (same L1) writes 1377 from the same base; the true number after both merge is 1381. Every other open collection-changing PR (P5 from this L1, and the other L1's phases) must merge `origin/main`, re-measure and rewrite the slots after this merges, or this PR does so if it merges second.
- `docs/INDEX.md`, `docs/_link_graph.json`: regenerated here; regenerate again after any other docs PR merges first.
- `docs/plans/2026-10-04-PROHIBITED-PARAPHRASE.md`: no other open work edits it (PR #49 is merged).
- No product file is touched, so there is no code overlap with P5 or any other phase.

Next action: the owner answers PARA-1 (A, B or C).
